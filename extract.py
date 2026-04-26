"""关键点抽取脚本 — 独立两阶段抽取入口

Usage:
    # 独立抽取模式
    python extract.py --datasets <roots> --cache-dir /tmp/ne

    # 强制重建缓存
    python extract.py --datasets <roots> --cache-dir /tmp/ne --force

    # 仅抽取指定数据集
    python extract.py --datasets dataset/GMDCSA24-A-Dataset-for-Human-Fall-Detection-in-Videos-v2.1 --cache-dir /tmp/ne
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

# 添加项目根目录到 path，确保导入一致
sys.path.insert(0, str(Path(__file__).parent))

from trainSTGCN import scan_gmdcsa24, scan_le2i
from yolo import load_pose_model

Path("log").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("log/extract.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# 缓存路径与读写
# ------------------------------------------------------------


def make_cache_key(task_desc: str, video_path: Path) -> str:
    """生成缓存文件名的 hash key"""
    rel = str(video_path).replace("\\", "/")
    sig = f"{task_desc}:{rel}"
    return hashlib.md5(sig.encode("utf-8")).hexdigest()[:16]


def build_cache_path(video_path: Path, task_desc: str, cache_root: Path) -> Path:
    """生成缓存文件路径"""
    key = make_cache_key(task_desc, video_path)
    subdir = cache_root / task_desc
    return subdir / f"{key}.npz"


def ensure_cache_dir(cache_root: Path, task_desc: str) -> Path:
    subdir = cache_root / task_desc
    subdir.mkdir(parents=True, exist_ok=True)
    return subdir


def save_cache(cache_data: dict, cache_path: Path) -> None:
    """保存 npz 缓存"""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache_path, **cache_data)


def load_cache(cache_path: Path) -> dict | None:
    """加载 npz 缓存，失败返回 None"""
    try:
        with np.load(cache_path) as data:
            return {k: data[k].item() if data[k].shape == () else data[k] for k in data.files}
    except Exception:
        return None


# ------------------------------------------------------------
# 关键点抽取（复用 train_stgcn.py 的逻辑）
# ------------------------------------------------------------


def get_video_dimensions(video_path: Path, task_desc: str) -> tuple[int, int]:
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


def extract_keypoints(video_path: Path, yolo_model, device: str) -> list[np.ndarray]:
    """从视频提取所有帧的关键点序列"""
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
            scores = result.boxes.conf.cpu().numpy()
            best_idx = int(np.argmax(scores))
            keypoints_list.append(kp[best_idx])
    cap.release()
    return keypoints_list


def extract_keypoints_from_images(image_folder: Path, yolo_model, device: str) -> list[np.ndarray]:
    """从 PNG 图像序列文件夹提取所有帧的关键点序列"""
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


def extract_single_video(
    video_path: Path,
    task_desc: str,
    label: int,
    fall_start: int | None,
    fall_end: int | None,
    yolo_model,
    device: str,
) -> dict:
    """抽取单个视频的关键点，返回缓存字典"""
    img_size = get_video_dimensions(video_path, task_desc)

    if task_desc == "urfall":
        kp_seq = extract_keypoints_from_images(video_path, yolo_model, device)
    else:
        kp_seq = extract_keypoints(video_path, yolo_model, device)

    return {
        "keypoints": np.array(kp_seq, dtype=np.float32) if kp_seq else np.zeros((0, 17, 3), dtype=np.float32),
        "img_size": img_size,
        "task_desc": task_desc,
        "label": label,
        "fall_start": fall_start,
        "fall_end": fall_end,
        "source_path": str(video_path),
    }


# ------------------------------------------------------------
# 任务扫描
# ------------------------------------------------------------


def scan_tasks(dataset_roots: list[Path], config: dict) -> list[tuple]:
    """扫描所有数据集，构建任务列表"""
    tasks: list[tuple] = []

    for root in dataset_roots:
        if not root.exists():
            logger.warning(f"数据集路径不存在: {root}")
            continue

        if "GMDCSA24" in str(root):
            tasks.extend(scan_gmdcsa24(root, config))
        elif any(x in str(root) for x in ["imvia", "le2i", "falldataset"]):
            tasks.extend(scan_le2i(root, config))
        elif "ur-fall" in str(root).lower():
            for folder in root.rglob("*-cam0-rgb"):
                if not folder.is_dir():
                    continue
                png_files = sorted(folder.glob("*.png"))
                if not png_files:
                    continue
                label = 1 if folder.name.lower().startswith("fall") else 0
                tasks.append(("urfall", folder, label, None, None))

    return tasks


# ------------------------------------------------------------
# 主抽取流程
# ------------------------------------------------------------


def run_extract(
    dataset_roots: list[str],
    config: dict,
    cache_root: str,
    force: bool,
    device: str,
    yolo_model_path: str,
):
    """执行关键点抽取"""
    cache_root = Path(cache_root)
    models_dir = config.get("models_dir", "models")

    logger.info("加载 YOLO 模型...")
    yolo = load_pose_model(yolo_model_path, models_dir=models_dir)

    logger.info("扫描数据集...")
    all_tasks = scan_tasks([Path(r) for r in dataset_roots], config)
    logger.info(f"共 {len(all_tasks)} 个任务待处理")

    stats = {"hit": 0, "miss": 0, "error": 0}

    for task_desc, video_path, label, fall_start, fall_end in tqdm(all_tasks, desc="抽取关键点", unit="video"):
        cache_path = build_cache_path(video_path, task_desc, cache_root)

        # 缓存命中检查
        if not force and cache_path.exists():
            data = load_cache(cache_path)
            if data is not None:
                stats["hit"] += 1
                logger.debug(f"缓存命中: {video_path.name}")
                continue
            logger.warning(f"缓存文件损坏，将重新抽取: {cache_path}")

        # 执行抽取
        try:
            cache_data = extract_single_video(
                video_path, task_desc, label, fall_start, fall_end, yolo, device
            )
            save_cache(cache_data, cache_path)
            stats["miss"] += 1
            logger.debug(f"已抽取并缓存: {video_path.name}")
        except Exception as e:
            stats["error"] += 1
            logger.error(f"抽取失败: {video_path} — {e}")

    logger.info("=" * 50)
    logger.info(f"抽取完成: 命中={stats['hit']}, 新抽={stats['miss']}, 失败={stats['error']}")
    logger.info(f"缓存目录: {cache_root}")


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------


def parse_args():
    parser = argparse.ArgumentParser(description="STGCN 关键点抽取（独立模式）")
    parser.add_argument("--cache-dir", type=str, default="/tmp/ne", help="缓存根目录")
    parser.add_argument("--force", action="store_true", help="强制重建已存在的缓存")
    parser.add_argument("--device", type=str, default="cuda" if __import__("torch").cuda.is_available() else "cpu")
    parser.add_argument("--yolo-model", type=str, default=None, help="YOLO 模型路径")
    parser.add_argument("--config", type=str, default="config/models.json", help="配置文件路径")
    parser.add_argument("--datasets", type=str, nargs="+", default=[], help="数据集根目录")
    return parser.parse_args()


def load_config(config_path: str = "config/models.json") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    args = parse_args()
    config = load_config(args.config)

    yolo_model = args.yolo_model or config.get("model", "yolo26x-pose.pt")
    dataset_roots = args.datasets or config.get("dataset_roots", [])

    if not dataset_roots:
        logger.error("未指定数据集路径，请使用 --datasets 参数或配置文件中 dataset_roots")
        return

    run_extract(
        dataset_roots=dataset_roots,
        config=config,
        cache_root=args.cache_dir,
        force=args.force,
        device=args.device,
        yolo_model_path=yolo_model,
    )


if __name__ == "__main__":
    main()
