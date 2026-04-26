"""CarePal 跌倒检测 Pipeline

支持 camera 模式和 dataset 模式，可选用几何条件或 STGCN 神经网络进行检测。

Usage:
    # 摄像头实时检测 (几何条件)
    python pipeline.py --mode camera --source 0 --method geometric

    # 摄像头实时检测 (STGCN 神经网络)
    python pipeline.py --mode camera --source 0 --method stgcn \
        --model out/20240422_120000/models/best_model.pth

    # 数据集评估
    python pipeline.py --mode dataset \
        --source dataset/GMDCSA24-A-Dataset-for-Human-Fall-Detection-in-Videos-v2.1 \
        --method geometric
"""

from __future__ import annotations

import argparse
import cv2
import json
import logging
import numpy as np
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import torch

from condition import check_fall as geometric_check_fall
from STGCN import STGCN_Pipeline
from yolo import load_pose_model, parse_source

# 确保日志目录存在
Path("log").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("log/pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# 配置加载
# ------------------------------------------------------------


def load_config(config_path: str = "config/models.json") -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------
# 几何跌倒检测器
# ------------------------------------------------------------


class GeometricDetector:
    """几何条件跌倒检测 — 使用骨骼关键点条件判断"""

    def __init__(self, conf_threshold: float = 0.5):
        self.conf_threshold = conf_threshold

    def detect(self, keypoints: np.ndarray, bbox: np.ndarray) -> Tuple[bool, str]:
        """检测单帧是否跌倒

        Args:
            keypoints: [17, 3] 关键点 (x, y, conf)
            bbox: [4] 边界框 (xmin, ymin, xmax, ymax)

        Returns:
            (is_fall, condition_msg)
        """
        return geometric_check_fall(keypoints, bbox, self.conf_threshold)


# ------------------------------------------------------------
# STGCN 跌倒检测器
# ------------------------------------------------------------


class STGCNDetector:
    """STGCN 神经网络跌倒检测 — 使用滑动窗口"""

    def __init__(
        self,
        model_path: str,
        window_size: int = 30,
        stride: int = 15,
        device: str = "cpu",
        conf_threshold: float = 0.5,
        streak_threshold: int = 5,
    ):
        self.pipeline = STGCN_Pipeline(
            model_path=model_path,
            num_classes=2,
            device=device,
            window_size=window_size,
            stride=stride,
        )
        self.conf_threshold = conf_threshold
        self.streak_threshold = streak_threshold
        self.buffer: deque = deque(maxlen=window_size)
        self.current_streak = 0
        self.max_streak = 0

    def detect_frame(self, keypoints: np.ndarray) -> Tuple[bool, float]:
        """将单帧关键点加入滑动窗口，触发检测

        Args:
            keypoints: [17, 3] 当前帧关键点

        Returns:
            (is_fall, conf)
        """
        self.buffer.append(keypoints)

        if len(self.buffer) < self.pipeline.window_size:
            return False, 0.0

        # 构建完整窗口
        seq = np.array(self.buffer)  # [T, 17, 3]

        # STGCN 推理
        pred, conf = self.pipeline.predict(seq)

        is_fall = pred == 1

        # 维护连续跌倒帧计数 (用于视频级判断)
        if is_fall:
            self.current_streak += 1
            if self.current_streak > self.max_streak:
                self.max_streak = self.current_streak
        else:
            self.current_streak = 0

        return is_fall, conf

    def reset(self):
        """重置滑动窗口状态"""
        self.buffer.clear()
        self.current_streak = 0
        self.max_streak = 0


# ------------------------------------------------------------
# YOLO 关键点提取器
# ------------------------------------------------------------


class YOLOKeypointExtractor:
    """YOLO-Pose 关键点提取"""

    def __init__(self, model_path: str, device: str = "cpu"):
        self.model = load_pose_model(model_path, models_dir=".")
        self.device = device

    def extract(self, frame: np.ndarray) -> List[Tuple[np.ndarray, np.ndarray]]:
        """从单帧提取所有人体关键点和边框

        Args:
            frame: RGB 图像

        Returns:
            List of [(keypoints, bbox), ...]  每个检测到的人
            keypoints: [17, 3]  bbox: [4]
        """
        results = self.model(frame, verbose=False)
        if not results:
            return []

        result = results[0]
        if result.keypoints is None or result.boxes is None:
            return []

        keypoints_list = result.keypoints.data.cpu().numpy()  # [N, 17, 3]
        boxes = result.boxes.xyxy.cpu().numpy()               # [N, 4]

        return [(kp, box) for kp, box in zip(keypoints_list, boxes)]


# ------------------------------------------------------------
# 视频级评估 (dataset 模式)
# ------------------------------------------------------------


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def calculate_metrics(tp: int, fp: int, tn: int, fn: int) -> Tuple[float, float, float]:
    precision = safe_divide(float(tp), float(tp + fp))
    recall = safe_divide(float(tp), float(tp + fn))
    f1 = safe_divide(2.0 * precision * recall, precision + recall)
    return precision, recall, f1


# ------------------------------------------------------------
# 核心推理循环
# ------------------------------------------------------------


def run_camera(
    source: Union[int, str],
    method: str,
    model_path: Optional[str] = None,
    device: str = "cpu",
    window_size: int = 30,
    stride: int = 15,
    streak_threshold: int = 5,
    yolo_model: str = "yolo26x-pose.pt",
    show: bool = True,
) -> None:
    """摄像头/视频文件实时检测"""

    # 加载检测器
    if method == "geometric":
        detector = GeometricDetector()
    elif method == "stgcn":
        if not model_path or not Path(model_path).exists():
            raise FileNotFoundError(f"STGCN 模型文件不存在: {model_path}")
        detector = STGCNDetector(
            model_path=model_path,
            window_size=window_size,
            stride=stride,
            device=device,
            streak_threshold=streak_threshold,
        )
    else:
        raise ValueError(f"未知方法: {method}")

    # 加载 YOLO
    extractor = YOLOKeypointExtractor(yolo_model, device)

    # 打开视频源
    cap = cv2.VideoCapture(source if isinstance(source, int) else str(source))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频源: {source}")

    window_name = "CarePal Fall Detection"
    if show:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        annotated = frame.copy()

        # YOLO 提取关键点
        detections = extractor.extract(frame)

        for keypoints, bbox in detections:
            if method == "geometric":
                is_fall, msg = detector.detect(keypoints, bbox)
                conf = 1.0
            else:
                is_fall, conf = detector.detect_frame(keypoints)
                msg = f"STGCN conf={conf:.2f}"

            # 绘制
            xmin, ymin, xmax, ymax = map(int, bbox)
            if is_fall:
                color = (0, 0, 255)
                label = f"FALL! {msg}"
            else:
                color = (0, 255, 0)
                label = f"Normal {msg}"

            cv2.rectangle(annotated, (xmin, ymin), (xmax, ymax), color, 2)
            cv2.putText(annotated, label, (xmin, max(ymin - 10, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        if show:
            cv2.imshow(window_name, annotated)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:
                break

    cap.release()
    if show:
        cv2.destroyAllWindows()
    logger.info(f"检测结束，共处理 {frame_idx} 帧")


def run_dataset(
    source: str,
    method: str,
    model_path: Optional[str] = None,
    device: str = "cpu",
    window_size: int = 30,
    stride: int = 15,
    streak_threshold: int = 5,
    yolo_model: str = "yolo26x-pose.pt",
) -> Dict[str, Any]:
    """数据集评估模式 — 遍历视频文件并输出视频级评估结果"""

    dataset_root = Path(source)
    if not dataset_root.exists():
        raise FileNotFoundError(f"数据集路径不存在: {source}")

    # 收集视频
    video_extensions = {".mp4", ".avi", ".mov", ".mkv"}
    videos: List[Tuple[Path, int]] = []  # (video_path, ground_truth_label)

    for file_path in dataset_root.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in video_extensions:
            continue
        parent_name = file_path.parent.name.lower()
        if parent_name == "adl":
            videos.append((file_path, 0))
        elif parent_name == "fall":
            videos.append((file_path, 1))
        elif parent_name in ("fall", "adl"):  # UR-Fall subdirs
            label = 1 if "fall" in parent_name else 0
            videos.append((file_path, label))

    videos.sort()
    logger.info(f"找到 {len(videos)} 个视频")

    # 加载检测器
    if method == "geometric":
        detector_fn = GeometricDetector()
    elif method == "stgcn":
        if not model_path or not Path(model_path).exists():
            raise FileNotFoundError(f"STGCN 模型文件不存在: {model_path}")
        detector_class = STGCNDetector
        detector_kwargs = dict(
            model_path=model_path,
            window_size=window_size,
            stride=stride,
            device=device,
            streak_threshold=streak_threshold,
        )
    else:
        raise ValueError(f"未知方法: {method}")

    tp = fp = tn = fn = 0
    results = []

    for video_path, gt_label in videos:
        logger.info(f"处理: {video_path.name}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.warning(f"无法打开: {video_path}")
            continue

        if method == "stgcn":
            detector = detector_class(**detector_kwargs)

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_idx = 0
        total_frames = 0
        fall_frames = 0
        current_streak = 0
        max_streak = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            total_frames += 1
            frame_has_fall = False

            # YOLO 提取关键点
            if method == "geometric":
                extractor = YOLOKeypointExtractor(yolo_model, device)
                detections = extractor.extract(frame)
                for keypoints, bbox in detections:
                    is_fall, _ = detector_fn.detect(keypoints, bbox)
                    frame_has_fall = frame_has_fall or is_fall
            else:
                extractor = YOLOKeypointExtractor(yolo_model, device)
                detections = extractor.extract(frame)
                for keypoints, bbox in detections:
                    is_fall, _ = detector.detect_frame(keypoints)
                    frame_has_fall = frame_has_fall or is_fall

            if frame_has_fall:
                fall_frames += 1
                current_streak += 1
                if current_streak > max_streak:
                    max_streak = current_streak
            else:
                current_streak = 0

            frame_idx += 1

        cap.release()

        # 视频级预测
        if method == "geometric":
            predicted_label = 1 if max_streak >= streak_threshold else 0
        else:
            predicted_label = 1 if max_streak >= streak_threshold else 0

        if gt_label == 1 and predicted_label == 1:
            tp += 1
        elif gt_label == 0 and predicted_label == 1:
            fp += 1
        elif gt_label == 0 and predicted_label == 0:
            tn += 1
        else:
            fn += 1

        results.append({
            "video": video_path.name,
            "path": str(video_path),
            "gt": gt_label,
            "pred": predicted_label,
            "total_frames": total_frames,
            "fall_frames": fall_frames,
            "max_streak": max_streak,
        })

        logger.info(f"  {video_path.name}: gt={gt_label}, pred={predicted_label}, "
                    f"max_streak={max_streak}, total={total_frames}, fall={fall_frames}")

    precision, recall, f1 = calculate_metrics(tp, fp, tn, fn)

    summary = {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "video_results": results,
    }

    logger.info("=" * 50)
    logger.info(f"评估完成: {len(results)} 个视频")
    logger.info(f"TP={tp}, FP={fp}, TN={tn}, FN={fn}")
    logger.info(f"Precision: {precision:.4f}")
    logger.info(f"Recall:    {recall:.4f}")
    logger.info(f"F1:        {f1:.4f}")

    return summary


# ------------------------------------------------------------
# CLI 入口
# ------------------------------------------------------------


def parse_args():
    parser = argparse.ArgumentParser(description="CarePal 跌倒检测 Pipeline")
    parser.add_argument(
        "--mode", type=str, choices=["camera", "dataset"], default="camera",
        help="camera: 实时检测; dataset: 数据集评估",
    )
    parser.add_argument(
        "--source", type=str, default="0",
        help="摄像头编号或视频/目录路径",
    )
    parser.add_argument(
        "--method", type=str, choices=["geometric", "stgcn"], default="geometric",
        help="geometric: 几何条件检测; stgcn: STGCN 神经网络",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="STGCN 模型文件路径 (.pth)",
    )
    parser.add_argument(
        "--yolo-model", type=str, default=None,
        help="YOLO Pose 模型路径",
    )
    parser.add_argument(
        "--config", type=str, default="config/models.json",
        help="配置文件路径",
    )
    parser.add_argument(
        "--device", type=str, default="cpu",
        help="推理设备 (cpu/cuda)",
    )
    parser.add_argument(
        "--no-show", action="store_true",
        help="不显示实时窗口",
    )
    parser.add_argument(
        "--streak-threshold", type=int, default=5,
        help="连续跌倒帧阈值 (视频级判断)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(args.config)

    # 加载超参数
    window_size = config.get("STGCN_window_size", 30)
    stride = config.get("STGCN_stride", 15)
    streak_threshold = args.streak_threshold or config.get("STGCN_fall_streak_threshold", 5)
    yolo_model = args.yolo_model or config.get("model", "yolo26x-pose.pt")

    source = parse_source(args.source)

    if args.mode == "camera":
        run_camera(
            source=source,
            method=args.method,
            model_path=args.model,
            device=args.device,
            window_size=window_size,
            stride=stride,
            streak_threshold=streak_threshold,
            yolo_model=yolo_model,
            show=not args.no_show,
        )
    else:
        summary = run_dataset(
            source=args.source,
            method=args.method,
            model_path=args.model,
            device=args.device,
            window_size=window_size,
            stride=stride,
            streak_threshold=streak_threshold,
            yolo_model=yolo_model,
        )


if __name__ == "__main__":
    main()
