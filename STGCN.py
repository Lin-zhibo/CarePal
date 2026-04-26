"""
STGCN: 基于时空图卷积网络的跌倒检测

节点(17个关键点)和边(骨骼连接)由 YOLO-Pose 检测提供,
跌倒标签由数据集标注文件解析获得.
"""

from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple, cast


# STGCN 神经网络


try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError as exc:
    raise ImportError("请安装 PyTorch: pip install torch") from exc



# COCO 17点骨骼连接 (由 YOLO-Pose 检测)

#   0=nose, 1=left_eye, 2=right_eye, 3=left_ear, 4=right_ear,
#   5=left_shoulder, 6=right_shoulder, 7=left_elbow, 8=right_elbow,
#   9=left_wrist, 10=right_wrist,
#   11=left_hip, 12=right_hip,
#   13=left_knee, 14=right_knee,
#   15=left_ankle, 16=right_ankle

COCO_EDGE: List[Tuple[int, int]] = [
    (0, 1),   # nose -> left_eye
    (0, 2),   # nose -> right_eye
    (1, 3),   # left_eye -> left_ear
    (2, 4),   # right_eye -> right_ear
    (5, 6),   # left_shoulder -> right_shoulder
    (5, 7),   # left_shoulder -> left_elbow
    (7, 9),   # left_elbow -> left_wrist
    (6, 8),   # right_shoulder -> right_elbow
    (8, 10),  # right_elbow -> right_wrist
    (5, 11),  # left_shoulder -> left_hip
    (6, 12),  # right_shoulder -> right_hip
    (11, 12), # left_hip -> right_hip
    (11, 13), # left_hip -> left_knee
    (13, 15), # left_knee -> left_ankle
    (12, 14), # right_hip -> right_knee
    (14, 16), # right_knee -> right_ankle
]

NUM_POINT = 17  # COCO 骨骼关键点数量

STGCN_LAYER_CHANNELS: Tuple[int, ...] = (64, 64, 64, 64, 128, 128, 128, 256, 256, 256)
STGCN_LAYER_STRIDES: Tuple[int, ...] = (1, 1, 1, 1, 2, 1, 1, 2, 1, 1)


    

def edge2mat(edges: List[Tuple[int, int]], num_point: int) -> np.ndarray:
    """将边列表转换为邻接矩阵

    注意: 采用 ST-GCN 常用定义 A[j, i] = 1，表示 i -> j。
    """
    A = np.zeros((num_point, num_point), dtype=np.float32)
    for i, j in edges:
        A[j, i] = 1.0
    return A


def normalize_digraph(A: np.ndarray) -> np.ndarray:
    """有向图归一化: A * D^{-1}"""
    Dl = np.sum(A, axis=0)
    num_point = A.shape[0]
    Dn = np.zeros((num_point, num_point), dtype=np.float32)
    for i in range(num_point):
        if Dl[i] > 0:
            Dn[i, i] = Dl[i] ** (-1)
    return np.dot(A, Dn)


def build_spatial_adjacency(edges: List[Tuple[int, int]], num_point: int) -> np.ndarray:
    """构建标准 ST-GCN 空间图邻接矩阵

    Args:
        edges: 骨骼连接边列表
        num_point: 关键点数量

    Returns:
        分区邻接矩阵 [K, num_point, num_point], 其中 K=3:
        [0] self-link, [1] inward, [2] outward
    """
    self_link = [(i, i) for i in range(num_point)]
    inward = edges
    outward = [(j, i) for i, j in inward]

    I = edge2mat(self_link, num_point)
    In = normalize_digraph(edge2mat(inward, num_point))
    Out = normalize_digraph(edge2mat(outward, num_point))
    return np.stack((I, In, Out), axis=0).astype(np.float32)


class SpatialGraphConv(nn.Module):
    """空间图卷积层

    标准 ST-GCN 实现:
    先用 1x1 卷积生成 K 个分区特征，再用 A[K, V, V] 做空间聚合。
    """

    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels * kernel_size, kernel_size=1)
        self.kernel_size = kernel_size

    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        # x: [B, C_in, T, V]  adj: [K, V, V]
        if adj.size(0) != self.kernel_size:
            raise ValueError(f"adj 的 K={adj.size(0)} 与 kernel_size={self.kernel_size} 不一致")

        x = self.conv(x)  # [B, C_out*K, T, V]
        n, kc, t, v = x.size()
        x = x.view(n, self.kernel_size, kc // self.kernel_size, t, v)  # [B, K, C_out, T, V]
        x = torch.einsum("nkctv,kvw->nctw", x, adj)
        return x.contiguous()


class STGCNUnit(nn.Module):
    """单个 ST-GCN 单元: GCN + TCN + 残差。"""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: Tuple[int, int],
        stride: int = 1,
        dropout: float = 0.0,
        residual: bool = True,
    ):
        super().__init__()
        assert len(kernel_size) == 2
        assert kernel_size[0] % 2 == 1

        padding = ((kernel_size[0] - 1) // 2, 0)
        self.gcn = SpatialGraphConv(in_channels, out_channels, kernel_size=kernel_size[1])
        self.tcn = nn.Sequential(
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=(kernel_size[0], 1),
                stride=(stride, 1),
                padding=padding,
            ),
            nn.BatchNorm2d(out_channels),
            nn.Dropout(dropout, inplace=True),
        )

        if not residual:
            self.residual = lambda x: 0
        elif in_channels == out_channels and stride == 1:
            self.residual = lambda x: x
        else:
            self.residual = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=(stride, 1)),
                nn.BatchNorm2d(out_channels),
            )

        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        x = self.tcn(self.gcn(x, adj)) + self.residual(x)
        return self.relu(x)


class ST_GCN(nn.Module):
    #仿照原论文repo ST-GCN

    def __init__(
        self,
        in_channels: int,
        num_class: int,
        num_point: int = NUM_POINT,
        edge_importance_weighting: bool = True,
        dropout: float = 0.5,
    ):
        super().__init__()

        A = torch.from_numpy(build_spatial_adjacency(COCO_EDGE, num_point))
        self.register_buffer("A", A)
        adj = cast(torch.Tensor, self.A)

        spatial_kernel_size = int(A.size(0))
        kernel_size = (9, spatial_kernel_size)
        self.data_bn = nn.BatchNorm1d(in_channels * num_point)

        self.st_gcn_networks = nn.ModuleList()
        for i, (out_channels, stride) in enumerate(
            zip(STGCN_LAYER_CHANNELS, STGCN_LAYER_STRIDES)
        ):
            in_dim = in_channels if i == 0 else STGCN_LAYER_CHANNELS[i - 1]
            self.st_gcn_networks.append(
                STGCNUnit(
                    in_dim,
                    out_channels,
                    kernel_size,
                    stride=stride,
                    dropout=0.0 if i == 0 else dropout,
                    residual=i != 0,
                )
            )

        self.edge_importance = nn.ParameterList(
            [
                nn.Parameter(torch.ones_like(adj), requires_grad=edge_importance_weighting)
                for _ in self.st_gcn_networks
            ]
        )

        self.fcn = nn.Conv2d(256, num_class, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [N, C, T, V, M]
        if x.ndim != 5:
            raise ValueError(f"期望输入维度为 [N, C, T, V, M]，实际为 {tuple(x.shape)}")

        n, c, t, v, m = x.size()
        adj = cast(torch.Tensor, self.A)
        x = x.permute(0, 4, 3, 1, 2).contiguous()
        x = x.view(n * m, v * c, t)
        x = self.data_bn(x)
        x = x.view(n, m, v, c, t)
        x = x.permute(0, 1, 3, 4, 2).contiguous()
        x = x.view(n * m, c, t, v)

        for gcn, importance in zip(self.st_gcn_networks, self.edge_importance):
            x = gcn(x, adj * importance)

        x = F.adaptive_avg_pool2d(x, (1, 1))
        x = x.view(n, m, -1, 1, 1).mean(dim=1)
        x = self.fcn(x)
        return x.view(x.size(0), -1)


class Model(nn.Module):
    """双流 ST-GCN: 原始序列流 + 运动差分流。"""

    def __init__(
        self,
        in_channels: int,
        num_class: int,
        num_point: int = NUM_POINT,
        edge_importance_weighting: bool = True,
        dropout: float = 0.5,
    ):
        super().__init__()
        self.origin_stream = ST_GCN(
            in_channels=in_channels,
            num_class=num_class,
            num_point=num_point,
            edge_importance_weighting=edge_importance_weighting,
            dropout=dropout,
        )
        self.motion_stream = ST_GCN(
            in_channels=in_channels,
            num_class=num_class,
            num_point=num_point,
            edge_importance_weighting=edge_importance_weighting,
            dropout=dropout,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [N, C, T, V, M]
        motion = torch.zeros_like(x)
        if x.size(2) > 2:
            motion[:, :, 1:-1] = x[:, :, 1:-1] - 0.5 * x[:, :, 2:] - 0.5 * x[:, :, :-2]
        return self.origin_stream(x) + self.motion_stream(motion)


class STGCN_FallDetection(nn.Module):
    """STGCN 跌倒检测模型

    输入: [B, T, V, C]
        B = batch size
        T = 帧数 (滑动窗口大小)
        V = 节点数 (17 个骨骼关键点，由 YOLO-Pose 检测)
        C = 特征维度 (x, y, confidence)

    输出: [B, num_classes]  2类: 0=正常, 1=跌倒
    """

    COCO_EDGE = COCO_EDGE
    NUM_POINT = NUM_POINT

    def __init__(
        self,
        in_channels: int = 3,
        num_classes: int = 2,
        num_point: int = NUM_POINT,
        hidden_dims: Optional[List[int]] = None,
        dropout: float = 0.5,
        edge_importance_weighting: bool = True,
    ):
        super().__init__()
        if hidden_dims is not None and list(hidden_dims) != [64, 128, 256]:
            raise ValueError(
                "原论文 ST-GCN 为固定 10 层结构，不支持自定义 hidden_dims。"
            )

        self.in_channels = in_channels
        self.num_point = num_point
        self.model = Model(
            in_channels=in_channels,
            num_class=num_classes,
            num_point=num_point,
            edge_importance_weighting=edge_importance_weighting,
            dropout=dropout,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, T, V, C] -> [B, C, T, V, M=1]
        if x.ndim != 4:
            raise ValueError(f"期望输入维度为 [B, T, V, C]，实际为 {tuple(x.shape)}")
        if x.size(-1) != self.in_channels:
            raise ValueError(f"输入通道数不匹配: 期望 {self.in_channels}, 实际 {x.size(-1)}")
        if x.size(2) != self.num_point:
            raise ValueError(f"关键点数不匹配: 期望 {self.num_point}, 实际 {x.size(2)}")

        x = x.permute(0, 3, 1, 2).contiguous().unsqueeze(-1)
        return self.model(x)


class STGCN_Pipeline:
    """STGCN 推理封装 — 适配 YOLO 关键点 + 滑动窗口"""

    def __init__(
        self,
        model_path: str,
        num_classes: int = 2,
        device: str = "cpu",
        window_size: int = 30,
        stride: int = 15,
    ):
        self.model = STGCN_FallDetection(num_classes=num_classes)
        state_dict = torch.load(model_path, map_location=device, weights_only=True)
        try:
            self.model.load_state_dict(state_dict)
        except RuntimeError as exc:
            raise RuntimeError(
                "模型权重与当前标准 ST-GCN 架构不匹配。请使用新架构重新训练得到的 checkpoint。"
            ) from exc
        self.model.to(device).eval()
        self.device = device
        self.num_classes = num_classes
        self.window_size = window_size
        self.stride = stride

    def preprocess(self, keypoints_seq: np.ndarray, img_size: tuple = (640, 640)) -> torch.Tensor:
        """关键点序列预处理

        Args:
            keypoints_seq: [T, 17, 3] 帧数×节点数×3(x,y,conf)
            img_size: 原始图像尺寸，用于归一化坐标
        """
        kp = keypoints_seq.copy()

        # 归一化坐标到 [0, 1]
        kp[:, :, 0] /= img_size[0]
        kp[:, :, 1] /= img_size[1]

        # 以髋部中心为原点 (使坐标与人体位置无关)
        hip_center = (kp[:, 11] + kp[:, 12]) / 2
        kp[:, :, :2] -= hip_center[:, np.newaxis, :2]

        return torch.from_numpy(kp).float().unsqueeze(0).to(self.device)

    @torch.no_grad()
    def predict(self, keypoints_seq: np.ndarray, img_size: tuple = (640, 640)) -> Tuple[int, float]:
        """推理

        Args:
            keypoints_seq: [T, 17, 3]

        Returns:
            (pred, conf)  pred: 类别索引 (0=正常, 1=跌倒), conf: 置信度
        """
        x = self.preprocess(keypoints_seq, img_size)
        logits = self.model(x)
        probs = torch.softmax(logits, dim=1)
        conf, pred = probs.max(dim=1)
        return int(pred.item()), float(conf.item())



# 数据集标注解析 — 提供跌倒标签 (用于训练)
# 关键点和边由 YOLO-Pose 检测，不从这里获取



def parse_gmdcsa24_csv(csv_path: str) -> List[Tuple[float, float]]:
    """GMDCSA24: 从 CSV 提取跌倒时间段 (秒)

    数据集标注格式:
        每个 Subject 目录下有 ADL.csv 和 Fall.csv
        CSV 列: File Name, Length (seconds), Time of Recording, Attire, Description, Classes
        Classes 示例: "Falling (SW)[3.4 to 6]; Sitting[0 to 3.4]"

    Returns:
        [(start_sec, end_sec), ...] 跌倒时间段列表
    """
    import pandas as pd

    df = pd.read_csv(csv_path, skiprows=1)
    fall_segments = []
    for _, row in df.iterrows():
        for seg in row[" Classes"].split("; "):
            if "Falling" in seg:
                times = seg.split("[")[1].rstrip("]")
                s, e = map(float, times.split(" to "))
                fall_segments.append((s, e))
    return fall_segments


def parse_imvia_annotation(txt_path: str) -> Tuple[Optional[int], Optional[int]]:
    """IMVIA / Le2i: 从 annotation txt 读跌倒起止帧

    数据集标注格式:
        第1行: 跌倒起始帧号
        第2行: 跌倒结束帧号
        第3行起: 每帧 "帧号,人ID,xmin,ymin,xmax,ymax"

    Returns:
        (fall_start_frame, fall_end_frame) 或 (None, None) 表示无跌倒
    """
    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    if len(lines) < 3:
        return None, None
    try:
        return int(lines[0].strip()), int(lines[1].strip())
    except ValueError:
        return None, None


def infer_ur_fall_label(video_path: Path) -> int:
    """UR-Fall: 从文件夹名推断视频级标签

    UR-Fall 没有帧级跌倒标注，只有文件夹名 (adl-/fall-) 区分活动类型。

    Returns:
        1 = fall 视频, 0 = adl 视频
    """
    parent = video_path.parent.name.lower()
    return 1 if parent.startswith("fall") else 0


def window_has_fall(
    window_start: int,
    window_end: int,
    fall_start: Optional[int],
    fall_end: Optional[int],
    video_label: int,
) -> bool:
    """判断滑动窗口是否包含跌倒帧

    Args:
        window_start: 窗口起始帧
        window_end: 窗口结束帧 (exclusive)
        fall_start: 跌倒起始帧 (IMVIA/GMDCSA24 有, UR-Fall 无)
        fall_end: 跌倒结束帧 (IMVIA/GMDCSA24 有, UR-Fall 无)
        video_label: 视频级标签 (0=adl, 1=fall)

    Returns:
        True if 窗口内包含跌倒
    """
    if video_label == 0:
        return False  # ADL 视频所有窗口均为负样本
    if fall_start is None or fall_end is None:
        return True  # 无帧级标注的 Fall 视频，全部窗口为正样本
    # 有帧级标注: 窗口与跌倒区间有交集即为正
    return window_start < fall_end and window_end > fall_start
