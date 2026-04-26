"""IMVIA/Le2i 数据集扫描

从 train_stgcn.py 的 scan_datasets() 中提取的 IMVIA/Le2i 部分。
"""

from pathlib import Path

from STGCN import parse_imvia_annotation


def scan_le2i(root: Path, config: dict) -> list[tuple]:
    """扫描 IMVIA/Le2i 数据集，构建任务列表

    Args:
        root: IMVIA/Le2i 数据集根目录
        config: 配置字典

    Returns:
        all_tasks 列表，每项为 (task_desc, video_path, label, fall_start, fall_end)
        task_desc == "imvia"
    """
    tasks = []

    for annotation_file in root.rglob("*.txt"):
        parent = annotation_file.parent
        video_name = annotation_file.stem.replace("video (", "video (").replace(")", ")")
        video_candidates = list(parent.glob(f"{video_name}.*")) or list(parent.glob("video (*).*"))
        if not video_candidates:
            continue
        video_path = video_candidates[0]
        fall_start, fall_end = parse_imvia_annotation(str(annotation_file))
        if fall_start is not None and fall_end is not None:
            fall_start = int(fall_start)
            fall_end = int(fall_end)
        tasks.append(("imvia", video_path, 1, fall_start, fall_end))

    return tasks
