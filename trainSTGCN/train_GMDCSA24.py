"""GMDCSA24 数据集扫描与窗口构建

从 train_stgcn.py 的 scan_datasets() 中提取的 GMDCSA24 部分。
"""

from pathlib import Path
import cv2
import pandas as pd

from STGCN import parse_gmdcsa24_csv, window_has_fall


def scan_gmdcsa24(root: Path, config: dict) -> list[tuple]:
    """扫描 GMDCSA24 数据集，构建任务列表

    Args:
        root: GMDCSA24 数据集根目录
        config: 配置字典

    Returns:
        all_tasks 列表，每项为 (task_desc, video_path, label, fall_start, fall_end)
        task_desc == "gmdcsa24"
    """
    window_size = config.get("STGCN_window_size", 30)
    tasks = []

    for subject_dir in root.rglob("Subject *"):
        for csv_name in ["ADL.csv", "Fall.csv"]:
            csv_path = subject_dir / csv_name
            if not csv_path.exists():
                continue
            is_fall_video = csv_name == "Fall.csv"
            try:
                csv_df = pd.read_csv(csv_path)
                video_names = csv_df["File Name"].tolist()
            except Exception:
                csv_df = None
                video_names = []

            for mp4_path in (subject_dir / ("Fall" if is_fall_video else "ADL")).glob("*.mp4"):
                fall_start, fall_end = None, None
                if is_fall_video and video_names and csv_df is not None:
                    try:
                        row_idx = video_names.index(mp4_path.name)
                        seg_str = csv_df.iloc[row_idx][" Classes"]
                        for seg in seg_str.split("; "):
                            if "Falling" in seg:
                                times = seg.split("[")[1].rstrip("]")
                                s, e = map(float, times.split(" to "))
                                cap_fps = cv2.VideoCapture(str(mp4_path)).get(cv2.CAP_PROP_FPS) or 30
                                fall_start = int(s * cap_fps)
                                fall_end = int(e * cap_fps)
                                break
                    except Exception:
                        pass
                tasks.append(("gmdcsa24", mp4_path, 1 if is_fall_video else 0, fall_start, fall_end))

    return tasks
