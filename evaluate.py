"""STGCN 测试集评估脚本

支持独立执行：
    python evaluate.py --model out/<timestamp>/models/best_model.pth \
        --test-dataset dataset/shahliza27/ur-fall-detection-dataset/versions/1/UR_fall_detection_dataset_cam0_rgb

训练完成后由 train_stgcn.py 调用：
    python evaluate.py --model out/<timestamp>/models/best_model.pth \
        --test-dataset <ur-fall-root> --config config/models.json --output out/<timestamp>/output.txt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path

import cv2
import numpy as np
import torch
from tqdm import tqdm

from STGCN import STGCN_Pipeline
from yolo import load_pose_model


# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


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


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def calculate_metrics(tp: int, fp: int, tn: int, fn: int):
    precision = safe_divide(float(tp), float(tp + fp))
    recall = safe_divide(float(tp), float(tp + fn))
    f1 = safe_divide(2.0 * precision * recall, precision + recall)
    return precision, recall, f1


def extract_keypoints(video_path: Path, yolo_model, device: str) -> list:
    """从视频文件提取所有帧的关键点序列"""
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


def get_img_size(video_path: Path, cache_hit: bool, cache_data: dict | None) -> tuple[int, int]:
    """获取图像/视频的原始尺寸，优先从缓存读取，否则直接读取"""
    if cache_hit and cache_data is not None:
        return tuple(cache_data["img_size"])
    if video_path.is_dir():
        first_img = next(video_path.glob("*.png"), None)
        if first_img is None:
            return (640, 640)
        frame = cv2.imread(str(first_img))
        if frame is None:
            return (640, 640)
        h, w = frame.shape[:2]
    else:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return (640, 640)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
    return (w, h)


def extract_keypoints_from_images(image_folder: Path, yolo_model, device: str) -> list:
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


def infer_ur_fall_label(video_path: Path) -> int:
    """UR-Fall: 从文件夹名推断视频级标签"""
    parent = video_path.parent.name.lower()
    return 1 if parent.startswith("fall") else 0


def scan_ur_fall(test_root: Path) -> list[tuple]:
    """扫描 UR-Fall 数据集，返回 (folder_path, label) 列表"""
    videos = []
    for folder in test_root.rglob("*-cam0-rgb"):
        if not folder.is_dir():
            continue
        png_files = sorted(folder.glob("*.png"))
        if not png_files:
            continue
        label = 1 if folder.name.lower().startswith("fall") else 0
        videos.append((folder, label))
    return videos


def evaluate_testset(
    model_path: str | Path,
    test_dataset_root: str | Path | list,
    config: dict,
    device: str,
    output_path: str | Path | None = None,
    cache_root: Path | None = None,
    force_cache: bool = False,
):
    """在测试集上进行视频级评估

    Args:
        model_path: 模型权重文件路径
        test_dataset_root: 测试数据集根目录（支持 UR-Fall PNG 序列），
                            也可以是已扫描好的列表 [(folder_path, label), ...]
        config: 配置字典
        device: 运行设备
        output_path: 输出文件路径，默认输出到模型同目录
    """
    window_size = config.get("STGCN_window_size", 30)
    stride = config.get("STGCN_stride", 15)
    streak_threshold = config.get("STGCN_fall_streak_threshold", 5)
    min_streak = config.get("STGCN_eval_min_streak", 3)
    positive_ratio_threshold = config.get("STGCN_eval_positive_ratio", 0.15)
    num_classes = config.get("STGCN_num_classes", 2)

    if output_path is None:
        output_path = Path(model_path).parent.parent / "output.txt"
    else:
        output_path = Path(output_path)

    logger.info("加载 YOLO 模型...")
    models_dir = config.get("models_dir", "models")
    yolo = load_pose_model(config.get("model", "yolo26x-pose.pt"), models_dir=models_dir)

    # 判断是路径列表还是已扫描好的数据
    if test_dataset_root and isinstance(test_dataset_root, list) and len(test_dataset_root) > 0:
        first = test_dataset_root[0]
        if isinstance(first, (list, tuple)):
            # 已扫描好的数据：[(video_path, label, kp_seq?), ...]
            test_videos = test_dataset_root
        else:
            # 路径列表，需要重新扫描
            test_roots = test_dataset_root
            test_videos = []
            for root in test_roots:
                root = Path(root)
                if not root.exists():
                    logger.warning(f"测试数据集路径不存在: {root}")
                    continue
                if "ur-fall" in str(root).lower():
                    test_videos.extend(scan_ur_fall(root))
                else:
                    logger.warning(f"未知测试数据集类型: {root}")
    elif isinstance(test_dataset_root, (str, Path)):
        # 单个路径
        test_roots = [test_dataset_root]
        test_videos = []
        for root in test_roots:
            root = Path(root)
            if not root.exists():
                logger.warning(f"测试数据集路径不存在: {root}")
                continue
            if "ur-fall" in str(root).lower():
                test_videos.extend(scan_ur_fall(root))
            else:
                logger.warning(f"未知测试数据集类型: {root}")
    else:
        test_videos = []

    if not test_videos:
        logger.warning("没有找到测试视频")
        return

    logger.info(f"共 {len(test_videos)} 个测试视频")

    # 创建 pipeline（内部加载模型权重）
    pipeline = STGCN_Pipeline(
        model_path=str(model_path),
        num_classes=num_classes,
        device=device,
        window_size=window_size,
        stride=stride,
    )

    tp = fp = tn = fn = 0
    results = []

    for video_path, gt_label in tqdm(test_videos, desc="Test set evaluation", unit="video"):
        vpath_str = str(video_path)
        task_desc = "urfall"  # UR-Fall 测试集固定为 urfall

        # 缓存查找
        cache_hit = False
        cache_data = None
        if cache_root is not None:
            cache_path = build_cache_path(vpath_str, task_desc, cache_root)
            if not force_cache and cache_path.exists():
                cache_data = load_cache(cache_path)
                if cache_data is not None:
                    kp_seq = list(cache_data["keypoints"])
                    cache_hit = True

        img_size = get_img_size(video_path, cache_hit, cache_data)

        # 缓存未命中：YOLO 抽取
        if not cache_hit:
            if video_path.is_dir():
                kp_seq = extract_keypoints_from_images(video_path, yolo, device)
            else:
                kp_seq = extract_keypoints(video_path, yolo, device)

            # 写回缓存
            if cache_root is not None and kp_seq:
                cache_data = {
                    "keypoints": np.array(kp_seq, dtype=np.float32),
                    "img_size": img_size,
                    "task_desc": task_desc,
                    "label": gt_label,
                    "fall_start": None,
                    "fall_end": None,
                    "source_path": vpath_str,
                }
                save_cache(cache_data, cache_path)

        if len(kp_seq) < window_size:
            logger.warning(f"视频关键点帧数不足 ({len(kp_seq)} < {window_size}): {video_path.name}")
            continue

        max_streak = 0
        current_streak = 0
        T = len(kp_seq)
        positive_count = 0

        for start in range(0, T - window_size + 1, stride):
            end = start + window_size
            window_seq = np.array(kp_seq[start:end])
            pred, conf = pipeline.predict(window_seq, img_size=img_size)
            if pred == 1:
                current_streak += 1
                positive_count += 1
                if current_streak > max_streak:
                    max_streak = current_streak
            else:
                current_streak = 0

        num_windows = (T - window_size) // stride + 1
        ratio = positive_count / num_windows if num_windows > 0 else 0
        predicted_label = 1 if (max_streak >= min_streak and ratio >= positive_ratio_threshold) else 0

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
            "max_streak": max_streak,
        })
        logger.info(f"  {video_path.name}: gt={gt_label}, pred={predicted_label}, max_streak={max_streak}")

    precision, recall, f1 = calculate_metrics(tp, fp, tn, fn)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("video_path\tgt\tpred\tmax_streak\n")
        for r in results:
            f.write(f"{r['video']}\t{r['gt']}\t{r['pred']}\t{r['max_streak']}\n")
        f.write(f"\nOverall\t{tp}\t{fp}\t{tn}\t{fn}\t{precision:.4f}\t{recall:.4f}\t{f1:.4f}\n")

    logger.info("=" * 50)
    logger.info(f"测试集视频级评估完成")
    logger.info(f"TP={tp}, FP={fp}, TN={tn}, FN={fn}")
    logger.info(f"Precision: {precision:.4f}")
    logger.info(f"Recall:    {recall:.4f}")
    logger.info(f"F1:        {f1:.4f}")
    logger.info(f"结果已保存到: {output_path}")


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="STGCN 测试集评估")
    parser.add_argument("--model", type=str, required=True, help="模型权重路径 (.pth)")
    parser.add_argument("--test-dataset", type=str, required=True, help="测试数据集根目录")
    parser.add_argument("--config", type=str, default="config/models.json")
    parser.add_argument("--output", type=str, default=None, help="输出结果文件路径")
    parser.add_argument(
        "--device", type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
    )
    parser.add_argument("--cache-dir", type=str, default=None, help="缓存根目录（默认 /tmp/ne）")
    parser.add_argument("--force-cache", action="store_true", help="强制重建缓存")
    args = parser.parse_args()

    config = load_config(args.config)

    cache_dir = args.cache_dir or config.get("cache_dir", "/tmp/ne")
    cache_root = Path(cache_dir) if cache_dir else None

    evaluate_testset(
        model_path=args.model,
        test_dataset_root=args.test_dataset,
        config=config,
        device=args.device,
        output_path=args.output,
        cache_root=cache_root,
        force_cache=args.force_cache,
    )


if __name__ == "__main__":
    main()
