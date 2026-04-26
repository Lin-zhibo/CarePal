"""STGCN 训练脚本 — K折交叉验证 + 测试集视频级评估

数据集划分:
  - GMDCSA24 / IMVIA/Le2i (有帧级标注) → 训练集
  - UR-Fall (无帧级标注) → 测试集

输出:
  - out/<timestamp>/models/best_model.pth
  - out/<timestamp>/img/metrics.png
  - out/<timestamp>/output.txt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from tqdm import tqdm
from torch.utils.data import DataLoader, Dataset
from sklearn.model_selection import KFold, GroupKFold

from STGCN import (
    STGCN_FallDetection,
    window_has_fall,
)
from yolo import load_pose_model
from evaluate import evaluate_testset


# 日志与输出目录


TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_DIR = Path("out") / TIMESTAMP
MODELS_DIR = OUT_DIR / "models"
IMG_DIR = OUT_DIR / "img"
for d in [MODELS_DIR, IMG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

Path("log").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"log/train_stgcn_{TIMESTAMP}.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)



# 配置加载


def load_config(config_path: str = "config/models.json") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------
# 缓存读写辅助函数
# ------------------------------------------------------------


def make_cache_key(task_desc: str, video_path: str) -> str:
    """生成缓存文件名的 hash key"""
    sig = f"{task_desc}:{video_path}"
    return hashlib.md5(sig.encode("utf-8")).hexdigest()[:16]


def build_cache_path(video_path: str, task_desc: str, cache_root: Path) -> Path:
    """生成缓存文件路径"""
    key = make_cache_key(task_desc, video_path)
    return cache_root / task_desc / f"{key}.npz"


def save_cache(cache_data: dict, cache_path: Path) -> None:
    """保存 npz 缓存"""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache_path, **cache_data)


def load_cache(cache_path: Path) -> dict | None:
    """加载 npz 缓存，失败返回 None"""
    try:
        with np.load(cache_path) as data:
            result = {}
            for k in data.files:
                val = data[k]
                result[k] = val.item() if val.shape == () else val
            return result
    except Exception:
        return None


# 关键点提取


def extract_keypoints(video_path: Path, yolo_model, device: str) -> list:
    """从视频提取所有帧的关键点序列

    Returns:
        List of [T, 17, 3] 关键点数组，按时间顺序排列
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.warning(f"无法打开视频: {video_path}")
        return []

    keypoints_list = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = yolo_model(frame, verbose=False)
        if not results:
            continue
        result = results[0]
        if result.keypoints is None or result.boxes is None:
            continue
        kp = result.keypoints.data.cpu().numpy()
        if len(kp) > 0:
            # 选择置信度最高的人
            scores = result.boxes.conf.cpu().numpy()
            best_idx = int(np.argmax(scores))
            keypoints_list.append(kp[best_idx])
    cap.release()
    return keypoints_list


def extract_keypoints_from_images(image_folder: Path, yolo_model, device: str) -> list:
    """从 PNG 图像序列文件夹提取所有帧的关键点序列

    用于 UR-Fall 等以图像序列形式存储的数据集。

    Returns:
        List of [17, 3] 关键点数组，按时间顺序排列
    """
    keypoints_list = []
    image_files = sorted(image_folder.glob("*.png"))
    for img_path in image_files:
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue
        results = yolo_model(frame, verbose=False)
        if not results:
            continue
        result = results[0]
        if result.keypoints is None or result.boxes is None:
            continue
        kp = result.keypoints.data.cpu().numpy()
        if len(kp) > 0:
            scores = result.boxes.conf.cpu().numpy()
            best_idx = int(np.argmax(scores))
            keypoints_list.append(kp[best_idx])
    return keypoints_list


def build_window_dataset(
    video_path: str,
    keypoints_seq: list,
    fall_start: int | None,
    fall_end: int | None,
    video_label: int,
    window_size: int,
    stride: int,
) -> list:
    """将视频的关键点序列拆分为滑动窗口样本

    Returns:
        List of (window_keypoints, label, video_path) 元组
    """
    T = len(keypoints_seq)
    windows = []
    for start in range(0, T - window_size + 1, stride):
        end = start + window_size
        label = 1 if window_has_fall(start, end, fall_start, fall_end, video_label) else 0
        seq = np.array(keypoints_seq[start:end])  # [T, 17, 3]
        windows.append((seq, label, str(video_path)))
    return windows



# 数据集扫描


def get_video_dimensions(video_path: Path, task_desc: str) -> tuple:
    """获取视频或图像序列的尺寸"""
    if task_desc == "urfall":
        png_files = sorted(video_path.glob("*.png"))
        if png_files:
            img = cv2.imread(str(png_files[0]))
            if img is not None:
                return (img.shape[1], img.shape[0])
    else:
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            if w > 0 and h > 0:
                return (w, h)
    return (640, 640)


def scan_datasets(dataset_roots: list, yolo_model, device: str, config: dict, cache_root: Path | None = None, force_cache: bool = False) -> tuple:
    """扫描所有数据集，构建训练/测试样本列表

    Args:
        cache_root: 缓存根目录，为 None 时不启用缓存
        force_cache: True 时强制重建缓存

    Returns:
        (train_windows, test_videos, img_sizes)
        train_windows: [(keypoints_seq, label, video_path), ...]
        test_videos: [(video_path, gt_label, keypoints_seq), ...]
        img_sizes: dict mapping video_path -> (width, height)
    """
    window_size = config.get("STGCN_window_size", 30)
    stride = config.get("STGCN_stride", 15)

    # 第一遍：收集所有待处理视频
    all_tasks: list[tuple] = []

    for root in dataset_roots:
        root = Path(root)
        if not root.exists():
            continue

        # GMDCSA24
        if "GMDCSA24" in str(root):
            from trainSTGCN import scan_gmdcsa24
            all_tasks.extend(scan_gmdcsa24(root, config))

        # IMVIA / Le2i
        elif any(x in str(root) for x in ["imvia", "le2i", "falldataset"]):
            from trainSTGCN import scan_le2i
            all_tasks.extend(scan_le2i(root, config))

        # UR-Fall — 支持 PNG 图像序列（每个文件夹为一视频）
        elif "ur-fall" in str(root).lower():
            for folder in root.rglob("*-cam0-rgb"):
                if not folder.is_dir():
                    continue
                png_files = sorted(folder.glob("*.png"))
                if not png_files:
                    continue
                label = 1 if folder.name.lower().startswith("fall") else 0
                all_tasks.append(("urfall", folder, label, None, None))

    # 第二遍：逐视频提取关键点，带视频级进度条
    train_windows = []
    test_videos = []
    img_sizes: dict[str, tuple[int, int]] = {}

    for task_desc, video_path, label, fall_start, fall_end in tqdm(all_tasks, desc="提取关键点", unit="video"):
        vpath_str = str(video_path)
        cache_hit = False

        # 缓存查找
        if cache_root is not None:
            cache_path = build_cache_path(vpath_str, task_desc, cache_root)
            if not force_cache and cache_path.exists():
                data = load_cache(cache_path)
                if data is not None:
                    kp_seq = list(data["keypoints"])
                    img_sizes[vpath_str] = tuple(data["img_size"])
                    cache_hit = True

        # 缓存未命中：YOLO 抽取
        if not cache_hit:
            img_sizes[vpath_str] = get_video_dimensions(video_path, task_desc)
            if task_desc == "urfall":
                kp_seq = extract_keypoints_from_images(video_path, yolo_model, device)
            else:
                kp_seq = extract_keypoints(video_path, yolo_model, device)

            # 写回缓存
            if cache_root is not None and kp_seq:
                cache_data = {
                    "keypoints": np.array(kp_seq, dtype=np.float32),
                    "img_size": img_sizes[vpath_str],
                    "task_desc": task_desc,
                    "label": label,
                    "fall_start": fall_start,
                    "fall_end": fall_end,
                    "source_path": vpath_str,
                }
                save_cache(cache_data, cache_path)

        if len(kp_seq) < window_size:
            continue
        windows = build_window_dataset(video_path, kp_seq, fall_start, fall_end, label, window_size, stride)
        if task_desc == "urfall":
            test_videos.append((video_path, label, kp_seq))
        else:
            train_windows.extend(windows)

    logger.info(f"训练窗口数: {len(train_windows)}, 测试视频数: {len(test_videos)}")
    return train_windows, test_videos, img_sizes






# 数据张量转换


class WindowDataset(Dataset):
    def __init__(self, windows: list, img_sizes: dict | None = None):
        self.windows = windows
        self.img_sizes = img_sizes or {}
        self.default_size = (640, 640)

    def __len__(self) -> int:
        return len(self.windows)

    def __getitem__(self, idx: int):
        kp_seq, label, video_path = self.windows[idx]
        T, V, C = kp_seq.shape
        img_size = self.img_sizes.get(video_path, self.default_size)
        kp = kp_seq.copy().astype(np.float32)
        kp[:, :, 0] /= img_size[0]
        kp[:, :, 1] /= img_size[1]
        hip_center = (kp[:, 11] + kp[:, 12]) / 2
        kp[:, :, :2] -= hip_center[:, np.newaxis, :2]
        x = torch.from_numpy(kp).float()
        y = torch.tensor(label, dtype=torch.long)
        return x, y


def collate_fn(batch):
    x = torch.stack([b[0] for b in batch])
    y = torch.stack([b[1] for b in batch])
    return x, y



# 指标计算


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def calculate_metrics(tp: int, fp: int, tn: int, fn: int) -> tuple:
    precision = safe_divide(float(tp), float(tp + fp))
    recall = safe_divide(float(tp), float(tp + fn))
    f1 = safe_divide(2.0 * precision * recall, precision + recall)
    return precision, recall, f1



# 训练循环


def train_epoch(model, dataloader, optimizer, criterion, device):
    model.train()
    total_loss = 0
    for x, y in tqdm(dataloader, desc="  Training", leave=False):
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * x.size(0)
    return total_loss / len(dataloader.dataset)


@torch.no_grad()
def evaluate(model, dataloader, device):
    model.eval()
    tp = fp = tn = fn = 0
    for x, y in tqdm(dataloader, desc="  Evaluating", leave=False):
        x, y = x.to(device), y.to(device)
        probs = torch.softmax(model(x), dim=1)
        preds = probs.argmax(dim=1)
        for p, t in zip(preds, y):
            if p == 1 and t == 1:
                tp += 1
            elif p == 1 and t == 0:
                fp += 1
            elif p == 0 and t == 0:
                tn += 1
            else:
                fn += 1
    precision, recall, f1 = calculate_metrics(tp, fp, tn, fn)
    return precision, recall, f1, tp, fp, tn, fn



# 主训练流程


def train_stgcn(
    dataset_roots: list,
    config: dict,
    epochs: int | None = None,
    batch_size: int | None = None,
    lr: float | None = None,
    n_folds: int | None = None,
    window_size: int | None = None,
    stride: int | None = None,
    device: str = "cpu",
    yolo_model_path: str = "yolo26x-pose.pt",
    cache_root: Path | None = None,
    force_cache: bool = False,
):
    # 超参数
    epochs = epochs or config.get("STGCN_epochs", 100)
    batch_size = batch_size or config.get("STGCN_batch_size", 32)
    lr = lr or config.get("STGCN_lr", 0.001)
    n_folds = n_folds or config.get("STGCN_n_folds", 5)
    window_size = window_size or config.get("STGCN_window_size", 30)
    stride = stride or config.get("STGCN_stride", 15)
    num_classes = config.get("STGCN_num_classes", 2)
    in_channels = config.get("STGCN_in_channels", 3)
    hidden_dims = config.get("STGCN_hidden_dims", [64, 128, 256])
    dropout = config.get("STGCN_dropout", 0.5)

    models_dir = config.get("models_dir", "models")
    logger.info("加载 YOLO 模型...")
    yolo = load_pose_model(yolo_model_path, models_dir=models_dir)

    logger.info("扫描数据集...")
    train_windows, test_videos, img_sizes = scan_datasets(dataset_roots, yolo, device, config, cache_root=cache_root, force_cache=force_cache)

    if len(train_windows) == 0:
        raise RuntimeError("没有找到训练样本")

    logger.info(f"共 {len(train_windows)} 个训练窗口，开始 K 折交叉验证...")

    # GroupKFold: 按视频分组，同一视频的所有窗口要么全在训练集，要么全在验证集
    groups = np.array([w[2] for w in train_windows])
    gkf = GroupKFold(n_splits=n_folds)
    fold_metrics = []

    # K 折交叉验证
    for fold, (train_idx, val_idx) in enumerate(gkf.split(train_windows, groups=groups)):
        logger.info(f"=== Fold {fold + 1}/{n_folds} ===")
        train_data = [train_windows[i] for i in train_idx]
        val_data = [train_windows[i] for i in val_idx]

        train_ds = WindowDataset(train_data, img_sizes=img_sizes)
        val_ds = WindowDataset(val_data, img_sizes=img_sizes)
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)

        model = STGCN_FallDetection(
            in_channels=in_channels,
            num_classes=num_classes,
            hidden_dims=hidden_dims,
            dropout=dropout,
        ).to(device)
        criterion = nn.CrossEntropyLoss(weight=torch.tensor([1.0, 3.0]).to(device))
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)

        best_f1 = 0
        best_state = None
        metrics = {"loss": [], "precision": [], "recall": [], "f1": []}

        for epoch in tqdm(range(epochs), desc=f"Fold {fold+1}/{n_folds}", unit="epoch"):
            train_loss = train_epoch(model, train_loader, optimizer, criterion, device)
            val_prec, val_rec, val_f1, _, _, _, _ = evaluate(model, val_loader, device)

            metrics["loss"].append(train_loss)
            metrics["precision"].append(val_prec)
            metrics["recall"].append(val_rec)
            metrics["f1"].append(val_f1)

            if val_f1 > best_f1:
                best_f1 = val_f1
                best_state = model.state_dict().copy()

            tqdm.write(f"  Epoch {epoch+1}/{epochs}: loss={train_loss:.4f}, val_f1={val_f1:.4f}")

        torch.save(best_state, MODELS_DIR / f"fold{fold + 1}_best.pth")
        logger.info(f"  Fold {fold + 1} 最优 F1: {best_f1:.4f}")
        fold_metrics.append(metrics)

    # 全量训练
    logger.info("=== 全量训练 (全部数据) ===")
    full_ds = WindowDataset(train_windows, img_sizes=img_sizes)
    full_loader = DataLoader(full_ds, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)

    model = STGCN_FallDetection(
        in_channels=in_channels,
        num_classes=num_classes,
        hidden_dims=hidden_dims,
        dropout=dropout,
    ).to(device)
    criterion = nn.CrossEntropyLoss(weight=torch.tensor([1.0, 3.0]).to(device))
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    best_f1 = 0
    best_state = None
    full_metrics = {"loss": [], "precision": [], "recall": [], "f1": []}

    for epoch in tqdm(range(epochs), desc="Full Training", unit="epoch"):
        train_loss = train_epoch(model, full_loader, optimizer, criterion, device)
        val_prec, val_rec, val_f1, _, _, _, _ = evaluate(model, full_loader, device)

        full_metrics["loss"].append(train_loss)
        full_metrics["precision"].append(val_prec)
        full_metrics["recall"].append(val_rec)
        full_metrics["f1"].append(val_f1)

        if val_f1 > best_f1:
            best_f1 = val_f1
            best_state = model.state_dict().copy()

        tqdm.write(f"  Epoch {epoch+1}/{epochs}: loss={train_loss:.4f}, val_f1={val_f1:.4f}")

    torch.save(best_state, MODELS_DIR / "best_model.pth")
    logger.info(f"全量训练完成，最优 F1: {best_f1:.4f}")

    # 绘制曲线
    plot_metrics(fold_metrics, full_metrics)

    # 保存训练信息（包含数据集路径，方便后续评估）
    train_info = {
        "timestamp": TIMESTAMP,
        "model_path": str(MODELS_DIR / "best_model.pth"),
        "val_f1": best_f1,
        "dataset_roots": dataset_roots,
    }
    with open(OUT_DIR / "train_info.json", "w", encoding="utf-8") as f:
        json.dump(train_info, f, indent=2, ensure_ascii=False)

    # 测试集评估（传入原始 dataset_roots，evaluate 自行过滤 UR-Fall）
    if test_videos:
        evaluate_testset(
            model_path=str(MODELS_DIR / "best_model.pth"),
            test_dataset_root=dataset_roots,
            config=config,
            device=device,
            output_path=str(OUT_DIR / "output.txt"),
            cache_root=cache_root,
            force_cache=force_cache,
        )



# 绘制指标曲线


def plot_metrics(fold_metrics: list, full_metrics: dict):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        names = ["loss", "precision", "recall", "f1"]

        for ax, name in zip(axes.flat, names):
            for i, fm in enumerate(fold_metrics):
                ax.plot(fm[name], alpha=0.5, label=f"Fold{i+1}_{name}")
            ax.plot(full_metrics[name], color="black", linewidth=2, label="Full")
            ax.set_title(name.capitalize())
            ax.set_xlabel("Epoch")
            ax.legend(fontsize=7)

        plt.tight_layout()
        plt.savefig(IMG_DIR / "metrics.png", dpi=150)
        plt.close()
        logger.info("指标曲线已保存到 img/metrics.png")
    except Exception as e:
        logger.warning(f"绘制曲线失败: {e}")


# CLI


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="STGCN 训练脚本")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--n-folds", type=int, default=None)
    parser.add_argument("--window-size", type=int, default=None)
    parser.add_argument("--stride", type=int, default=None)
    parser.add_argument("--device", type=str, default="cuda" if __import__("torch").cuda.is_available() else "cpu")
    parser.add_argument("--yolo-model", type=str, default=None)
    parser.add_argument("--config", type=str, default="config/models.json")
    parser.add_argument("--datasets", type=str, nargs="+", default=[])
    parser.add_argument("--cache-dir", type=str, default=None, help="缓存根目录（默认 /tmp/ne）")
    parser.add_argument("--force-cache", action="store_true", help="强制重建缓存")
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(args.config)

    yolo_model = args.yolo_model or config.get("model", "yolo26x-pose.pt")

    # 从配置读取数据集路径，支持命令行覆盖
    dataset_roots = args.datasets or config.get("dataset_roots", [])

    # 缓存目录：CLI > config > 默认 /tmp/ne
    cache_dir = args.cache_dir or config.get("cache_dir", "/tmp/ne")
    cache_root = Path(cache_dir) if cache_dir else None

    train_stgcn(
        dataset_roots=dataset_roots,
        config=config,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        n_folds=args.n_folds,
        window_size=args.window_size,
        stride=args.stride,
        device=args.device,
        yolo_model_path=yolo_model,
        cache_root=cache_root,
        force_cache=args.force_cache,
    )


if __name__ == "__main__":
    main()