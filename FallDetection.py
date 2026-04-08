#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
from ultralytics import YOLO

from condition import check_fall

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}


# Function: safe_divide
# Parameters:
#   numerator (float): The dividend value. Valid range is any finite float.
#   denominator (float): The divisor value. Valid range is any finite float, including zero.
# Return:
#   float: The division result when denominator is non-zero; otherwise 0.0.
# Description: Performs safe division and prevents division-by-zero errors during metric calculation.
def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


# Function: calculate_metrics
# Parameters:
#   tp (int): Number of true positives. Valid range is integers >= 0.
#   fp (int): Number of false positives. Valid range is integers >= 0.
#   tn (int): Number of true negatives. Valid range is integers >= 0.
#   fn (int): Number of false negatives. Valid range is integers >= 0.
# Return:
#   tuple: (precision, recall, f1), all floats in [0.0, 1.0].
# Description: Calculates binary-classification Precision, Recall, and F1 score from confusion-matrix counts.
def calculate_metrics(tp: int, fp: int, tn: int, fn: int) -> Tuple[float, float, float]:
    _ = tn
    precision = safe_divide(float(tp), float(tp + fp))
    recall = safe_divide(float(tp), float(tp + fn))
    f1 = safe_divide(2.0 * precision * recall, precision + recall)
    return precision, recall, f1


# Function: infer_ground_truth_label
# Parameters:
#   video_path (Path): Absolute or relative path of a video file. Parent folder is expected to be ADL or Fall.
# Return:
#   Optional[int]: Returns 0 for ADL (non-fall), 1 for Fall, and None if label cannot be inferred.
# Description: Infers the video-level ground-truth label from the direct parent directory name.
def infer_ground_truth_label(video_path: Path) -> Optional[int]:
    parent_name = video_path.parent.name.lower()
    if parent_name == "adl":
        return 0
    if parent_name == "fall":
        return 1
    return None


# Function: collect_dataset_videos
# Parameters:
#   dataset_source (Path): Dataset root directory or a single video path. Valid path should exist on disk.
# Return:
#   tuple: (sources, label_map, skipped_count)
#     - sources (List[str]): Collected video paths for evaluation.
#     - label_map (Dict[str, int]): Mapping from video path to ground-truth label (0/1).
#     - skipped_count (int): Number of video files skipped due to missing ADL/Fall label folders.
# Description: Collects supported video files and maps each file to its ADL/Fall ground-truth label.
def collect_dataset_videos(dataset_source: Path) -> Tuple[List[str], Dict[str, int], int]:
    if not dataset_source.exists():
        return [], {}, 0

    sources: List[str] = []
    label_map: Dict[str, int] = {}
    skipped_count = 0

    if dataset_source.is_file():
        if dataset_source.suffix.lower() not in VIDEO_EXTENSIONS:
            return [], {}, 1

        resolved_file = str(dataset_source.resolve())
        label = infer_ground_truth_label(Path(resolved_file))
        if label is None:
            return [], {}, 1

        sources.append(resolved_file)
        label_map[resolved_file] = label
        return sources, label_map, 0

    for file_path in dataset_source.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        resolved_file = str(file_path.resolve())
        label = infer_ground_truth_label(Path(resolved_file))
        if label is None:
            skipped_count += 1
            continue

        sources.append(resolved_file)
        label_map[resolved_file] = label

    sources.sort()
    return sources, label_map, skipped_count


# Function: main
# Parameters:
#   None.
# Return:
#   None.
# Description: Entry point of the script. Handles CLI arguments, performs frame inference,
# aggregates dataset-mode results at video level, and prints Precision/Recall/F1.
def main() -> None:
    parser = argparse.ArgumentParser(description="CarePal: Fall Detection Pipeline.")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["camera", "dataset"],
        default="camera",
        help="Mode: 'camera' for real-time webcam, 'dataset' for dataset evaluation",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help="Video path or camera index (default 0), or directory path for dataset mode",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="models/yolo26x-pose.pt",
        help="Path to YOLO pose model weights",
    )
    parser.add_argument(
        "--fall-streak-threshold",
        type=int,
        default=5,
        help="Minimum consecutive fall-positive frames to classify a video as fall in dataset mode",
    )
    args = parser.parse_args()

    if args.fall_streak_threshold < 1:
        print("Error: --fall-streak-threshold must be >= 1")
        return

    csv_file = None
    csv_writer = None
    csv_path: Optional[Path] = None
    dataset_dir: Optional[Path] = None
    dataset_output_root: Optional[Path] = None
    ground_truth_map: Dict[str, int] = {}
    skipped_unlabeled = 0

    tp = fp = tn = fn = 0
    processed_videos = 0
    failed_videos = 0

    if args.mode == "dataset":
        dataset_dir = Path(args.source) if args.source != "0" else Path("dataset")
        dataset_output_root = dataset_dir.resolve().parent if dataset_dir.is_file() else dataset_dir.resolve()
        sources, ground_truth_map, skipped_unlabeled = collect_dataset_videos(dataset_dir)
        if not sources:
            print(f"Error: No labeled videos found in {dataset_dir}")
            return

        out_dir = Path("output")
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / "result.csv"
        csv_file = open(csv_path, "w", newline="", encoding="utf-8")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(
            [
                "video_name",
                "video_path",
                "ground_truth_fall",
                "predicted_fall",
                "total_frames",
                "fall_frames",
                "max_fall_streak",
                "streak_threshold",
            ]
        )

        print(f"Found {len(sources)} labeled videos in dataset. Results will be saved to {csv_path}")
        if skipped_unlabeled > 0:
            print(f"Skipped {skipped_unlabeled} videos because they are not inside ADL/Fall directories.")
    else:
        sources = [args.source]

    print(f"Loading YOLO model from {args.model}...")
    model = YOLO(args.model)

    window_name = "CarePal Fall Detection"
    if args.mode == "camera":
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    try:
        for source_path in sources:
            if args.mode == "dataset":
                print(f"\nProcessing video: {source_path}...")

            try:
                source_idx = int(source_path)
                cap = cv2.VideoCapture(source_idx)
            except ValueError:
                cap = cv2.VideoCapture(source_path)

            if not cap.isOpened():
                print(f"Error: Could not open video source {source_path}")
                if args.mode == "dataset":
                    failed_videos += 1
                continue

            quit_flag = False
            total_frames = 0
            fall_frames = 0
            current_streak = 0
            max_streak = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                total_frames += 1

                results = model(frame, verbose=False)
                result = results[0]

                annotated_frame = result.plot() if args.mode == "camera" else None
                frame_has_fall = False

                if result.keypoints is not None and result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    keypoints = result.keypoints.data.cpu().numpy()

                    for bbox, kp in zip(boxes, keypoints):
                        is_fall, condition_msg = check_fall(kp, bbox)
                        frame_has_fall = frame_has_fall or is_fall

                        if args.mode == "camera" and annotated_frame is not None:
                            xmin, ymin, xmax, ymax = map(int, bbox)
                            if is_fall:
                                cv2.rectangle(annotated_frame, (xmin, ymin), (xmax, ymax), (0, 0, 255), 4)
                                text_alert = f"FALL! {condition_msg}"
                                (tw, _), _ = cv2.getTextSize(
                                    text_alert, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2
                                )
                                cv2.rectangle(
                                    annotated_frame,
                                    (xmin, ymin - 30),
                                    (xmin + tw, ymin),
                                    (0, 0, 255),
                                    -1,
                                )
                                cv2.putText(
                                    annotated_frame,
                                    text_alert,
                                    (xmin, ymin - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.8,
                                    (255, 255, 255),
                                    2,
                                    cv2.LINE_AA,
                                )
                            else:
                                cv2.putText(
                                    annotated_frame,
                                    "NORMAL",
                                    (xmin, max(ymin - 10, 0)),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.7,
                                    (0, 255, 0),
                                    2,
                                    cv2.LINE_AA,
                                )

                if args.mode == "dataset":
                    if frame_has_fall:
                        fall_frames += 1
                        current_streak += 1
                        if current_streak > max_streak:
                            max_streak = current_streak
                    else:
                        current_streak = 0

                if args.mode == "camera" and annotated_frame is not None:
                    cv2.imshow(window_name, annotated_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q") or key == 27:
                        quit_flag = True
                        break

            cap.release()

            if args.mode == "dataset" and csv_writer is not None:
                ground_truth_label = ground_truth_map.get(source_path)
                if ground_truth_label is None:
                    print(f"Warning: Missing ADL/Fall label for {source_path}, skipped in metrics.")
                    continue

                predicted_label = int(max_streak >= args.fall_streak_threshold)

                if ground_truth_label == 1 and predicted_label == 1:
                    tp += 1
                elif ground_truth_label == 0 and predicted_label == 1:
                    fp += 1
                elif ground_truth_label == 0 and predicted_label == 0:
                    tn += 1
                else:
                    fn += 1

                processed_videos += 1

                video_name = Path(source_path).name
                video_path_output = Path(source_path).as_posix()
                if dataset_output_root is not None:
                    try:
                        video_path_output = (
                            Path(source_path).resolve().relative_to(dataset_output_root).as_posix()
                        )
                    except ValueError:
                        video_path_output = Path(source_path).as_posix()

                csv_writer.writerow(
                    [
                        video_name,
                        video_path_output,
                        ground_truth_label,
                        predicted_label,
                        total_frames,
                        fall_frames,
                        max_streak,
                        args.fall_streak_threshold,
                    ]
                )

            if quit_flag:
                break
    finally:
        if csv_file is not None:
            csv_file.close()

    if args.mode == "camera":
        cv2.destroyAllWindows()
    else:
        precision, recall, f1 = calculate_metrics(tp, fp, tn, fn)

        print("\nDataset evaluation complete.")
        if csv_path is not None:
            print(f"Video-level results written to {csv_path}")
        print(f"Evaluated videos: {processed_videos}")
        print(f"Failed to open videos: {failed_videos}")
        print("Confusion Matrix (video-level):")
        print(f"TP={tp}, FP={fp}, TN={tn}, FN={fn}")
        print(f"Precision: {precision:.4f}")
        print(f"Recall: {recall:.4f}")
        print(f"F1 Score: {f1:.4f}")


if __name__ == "__main__":
    main()