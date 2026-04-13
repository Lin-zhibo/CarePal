from __future__ import annotations

import csv
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

import cv2
import numpy as np
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from condition import check_fall


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
LOGGER = logging.getLogger(__name__)

FALSE_POSITIVE_GT = 0
FALSE_POSITIVE_PRED = 1
DEFAULT_STREAK_THRESHOLD = 5
SEEK_SECONDS = 3

KEY_QUIT = {ord("q"), ord("Q"), 27}
KEY_NEXT = {ord("n"), ord("N")}
KEY_PAUSE = {ord(" ")}
# waitKeyEx arrow codes: Windows(2424832/2555904), Linux/X11(65361/65363)
KEY_LEFT = {2424832, 65361}
KEY_RIGHT = {2555904, 65363}


@dataclass(frozen=True)
class FalsePositiveVideo:
    video_name: str
    video_path: str
    ground_truth_fall: int
    predicted_fall: int
    total_frames: int
    fall_frames: int
    max_fall_streak: int
    streak_threshold: int


# Function:
#   parse_int_field
# Parameters:
#   row (Mapping[str, str]): A CSV row mapping field names to text values.
#   field_name (str): The target integer field key in the CSV row.
#   default_value (int): Fallback integer when value is missing or invalid; any integer is valid.
# Returns:
#   int: Parsed integer value for the field, or default_value when parsing fails.
# Description:
#   Safely parses integer values from CSV rows to keep data loading robust.
def parse_int_field(row: Mapping[str, str], field_name: str, default_value: int = 0) -> int:
    raw_value = str(row.get(field_name, "")).strip()
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default_value


# Function:
#   load_model_config
# Parameters:
#   config_path (Path): Absolute path to the JSON config file; must point to a readable file.
# Returns:
#   Dict[str, str]: Dictionary containing "model" and "models_dir" keys.
# Description:
#   Loads and validates model configuration used for YOLO inference.
def load_model_config(config_path: Path) -> Dict[str, str]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as config_file:
        config_data = json.load(config_file)

    if not isinstance(config_data, dict):
        raise ValueError("Model config must be a JSON object")

    model_name = str(config_data.get("model", "")).strip()
    models_dir = str(config_data.get("models_dir", "models")).strip() or "models"

    if not model_name:
        raise ValueError("Model config must contain a non-empty 'model' field")

    return {"model": model_name, "models_dir": models_dir}


# Function:
#   resolve_model_weight_path
# Parameters:
#   project_root (Path): Project root directory path; must exist.
#   model_config (Mapping[str, str]): Model config containing "model" and "models_dir" values.
# Returns:
#   Path: Absolute model file path for YOLO loading.
# Description:
#   Resolves possible model file locations and returns the first existing candidate.
def resolve_model_weight_path(project_root: Path, model_config: Mapping[str, str]) -> Path:
    model_raw_path = Path(model_config["model"])
    models_dir = Path(model_config["models_dir"])

    candidate_paths: List[Path] = []
    if model_raw_path.is_absolute():
        candidate_paths.append(model_raw_path)
    else:
        candidate_paths.append((project_root / model_raw_path).resolve())
        candidate_paths.append((project_root / models_dir / model_raw_path).resolve())
        candidate_paths.append((project_root / "models" / model_raw_path.name).resolve())

    seen: set[str] = set()
    deduplicated: List[Path] = []
    for candidate in candidate_paths:
        candidate_text = str(candidate)
        if candidate_text in seen:
            continue
        seen.add(candidate_text)
        deduplicated.append(candidate)

    for candidate in deduplicated:
        if candidate.exists():
            return candidate

    missing_candidates = ", ".join(str(path) for path in deduplicated)
    raise FileNotFoundError(
        "Model file was not found in any candidate path: "
        f"{missing_candidates}"
    )


# Function:
#   load_false_positive_videos
# Parameters:
#   csv_path (Path): Path to result CSV file; file must contain required columns.
# Returns:
#   List[FalsePositiveVideo]: Ordered false-positive entries where GT=0 and Pred=1.
# Description:
#   Reads result.csv and filters all false-positive videos while preserving CSV row order.
def load_false_positive_videos(csv_path: Path) -> List[FalsePositiveVideo]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Result CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required_fields = {
            "video_name",
            "video_path",
            "ground_truth_fall",
            "predicted_fall",
            "total_frames",
            "fall_frames",
            "max_fall_streak",
            "streak_threshold",
        }

        if reader.fieldnames is None:
            raise ValueError("Result CSV is missing header row")

        missing_fields = required_fields.difference(set(reader.fieldnames))
        if missing_fields:
            missing_text = ", ".join(sorted(missing_fields))
            raise ValueError(f"Result CSV missing required fields: {missing_text}")

        false_positives: List[FalsePositiveVideo] = []
        for row_index, row in enumerate(reader, start=2):
            ground_truth = parse_int_field(row, "ground_truth_fall", default_value=-1)
            predicted = parse_int_field(row, "predicted_fall", default_value=-1)

            if ground_truth not in {0, 1} or predicted not in {0, 1}:
                LOGGER.warning(
                    "Skip invalid label row at line %d: ground_truth_fall=%s, predicted_fall=%s",
                    row_index,
                    row.get("ground_truth_fall", ""),
                    row.get("predicted_fall", ""),
                )
                continue

            if ground_truth != FALSE_POSITIVE_GT or predicted != FALSE_POSITIVE_PRED:
                continue

            false_positives.append(
                FalsePositiveVideo(
                    video_name=str(row.get("video_name", "")).strip(),
                    video_path=str(row.get("video_path", "")).strip(),
                    ground_truth_fall=ground_truth,
                    predicted_fall=predicted,
                    total_frames=parse_int_field(row, "total_frames", default_value=0),
                    fall_frames=parse_int_field(row, "fall_frames", default_value=0),
                    max_fall_streak=parse_int_field(row, "max_fall_streak", default_value=0),
                    streak_threshold=parse_int_field(
                        row,
                        "streak_threshold",
                        default_value=DEFAULT_STREAK_THRESHOLD,
                    ),
                )
            )

        return false_positives


# Function:
#   resolve_dataset_video_path
# Parameters:
#   project_root (Path): Project root path containing dataset directory.
#   video_relative_path (str): Relative path from CSV; accepts forward or backward slashes.
# Returns:
#   Path: Absolute path to the expected dataset video file.
# Description:
#   Normalizes the CSV path format and maps it to the local dataset directory.
def resolve_dataset_video_path(project_root: Path, video_relative_path: str) -> Path:
    normalized_relative_path = video_relative_path.replace("\\", "/").lstrip("./")
    return (project_root / "dataset" / Path(normalized_relative_path)).resolve()


# Function:
#   get_video_fps
# Parameters:
#   cap (cv2.VideoCapture): OpenCV video capture object; should already be opened.
# Returns:
#   float: Valid video fps value, defaulting to 30.0 when source metadata is invalid.
# Description:
#   Retrieves playback fps from video metadata while guarding against invalid values.
def get_video_fps(cap: cv2.VideoCapture) -> float:
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 0.0 or np.isnan(fps) or np.isinf(fps):
        LOGGER.warning("Invalid FPS metadata detected. Fallback to 30.0 FPS.")
        return 30.0
    return fps


# Function:
#   get_frame_delay_ms
# Parameters:
#   fps (float): Video frames-per-second value; must be positive for normal operation.
# Returns:
#   int: Milliseconds delay per frame, clamped to at least 1 ms.
# Description:
#   Converts fps into waitKey delay to match source playback speed.
def get_frame_delay_ms(fps: float) -> int:
    if fps <= 0.0:
        return 33
    return max(1, int(round(1000.0 / fps)))


# Function:
#   seek_video_by_seconds
# Parameters:
#   cap (cv2.VideoCapture): OpenCV capture object to seek; must be opened.
#   seconds (float): Signed seek amount in seconds; positive seeks forward, negative seeks backward.
#   fps (float): Playback fps used to convert seconds to frame count; should be positive.
# Returns:
#   int: Final target frame index after clamping to available range.
# Description:
#   Repositions playback by a fixed time offset while staying inside valid frame bounds.
def seek_video_by_seconds(cap: cv2.VideoCapture, seconds: float, fps: float) -> int:
    delta_frames = int(round(seconds * fps))
    current_frame_index = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    target_frame = current_frame_index + delta_frames
    if total_frames > 0:
        target_frame = max(0, min(total_frames - 1, target_frame))
    else:
        target_frame = max(0, target_frame)

    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    return target_frame


# Function:
#   evaluate_frame
# Parameters:
#   model (YOLO): Loaded YOLO pose model used for per-frame human pose inference.
#   frame (np.ndarray): BGR image frame from OpenCV; shape [H, W, 3].
# Returns:
#   Tuple[np.ndarray, bool, List[str]]: Annotated frame, frame-level fall flag, and per-person reason texts.
# Description:
#   Runs YOLO on one frame and evaluates all detected persons via check_fall to produce reasons.
def evaluate_frame(model: YOLO, frame: np.ndarray) -> Tuple[np.ndarray, bool, List[str]]:
    try:
        results = model(frame, verbose=False)
        if not results:
            return frame, False, ["No inference result"]

        result = results[0]
        annotated_frame = result.plot()

        if result.keypoints is None or result.boxes is None:
            return annotated_frame, False, ["No person detected"]

        boxes = result.boxes.xyxy.cpu().numpy()
        keypoints = result.keypoints.data.cpu().numpy()

        if boxes.size == 0 or keypoints.size == 0:
            return annotated_frame, False, ["No person detected"]
    except Exception as error:  # pragma: no cover - runtime environment dependent
        LOGGER.error("Frame evaluation failed: %s", error)
        return frame, False, [f"Frame evaluation error: {str(error)[:80]}"]

    frame_has_fall = False
    person_reasons: List[str] = []

    for person_index, (bbox, kp) in enumerate(zip(boxes, keypoints), start=1):
        is_fall, condition_message = check_fall(kp, bbox)

        if is_fall:
            frame_has_fall = True
            reason_text = condition_message if condition_message else "ConditionUnknown"
            person_reasons.append(f"P{person_index}: FALL {reason_text}")

            xmin, ymin, xmax, ymax = map(int, bbox[:4])
            cv2.rectangle(annotated_frame, (xmin, ymin), (xmax, ymax), (0, 0, 255), 3)
        else:
            person_reasons.append(f"P{person_index}: NORMAL")

    if len(boxes) != len(keypoints):
        mismatch_reason = (
            f"Warning: box/keypoint count mismatch ({len(boxes)} vs {len(keypoints)})"
        )
        LOGGER.warning(mismatch_reason)
        person_reasons.append(mismatch_reason)

    return annotated_frame, frame_has_fall, person_reasons


# Function:
#   draw_overlay
# Parameters:
#   frame (np.ndarray): BGR frame to annotate; shape [H, W, 3].
#   top_lines (Sequence[str]): Global status lines such as labels and controls.
#   reason_lines (Sequence[str]): Per-person reason lines to display for current frame.
# Returns:
#   np.ndarray: Frame copy with translucent information panel and text overlay.
# Description:
#   Renders playback metadata and frame-level reason text onto the displayed frame.
def draw_overlay(frame: np.ndarray, top_lines: Sequence[str], reason_lines: Sequence[str]) -> np.ndarray:
    overlay_frame = frame.copy()

    display_lines: List[str] = list(top_lines)
    display_lines.append("Frame reasons:")
    display_lines.extend(reason_lines)

    line_height = 24
    padding = 12
    x0 = 10
    y0 = 10

    max_text_width = 0
    for line in display_lines:
        (text_width, _), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        if text_width > max_text_width:
            max_text_width = text_width

    panel_width = min(frame.shape[1] - 20, max_text_width + 2 * padding)
    panel_height = min(frame.shape[0] - 20, len(display_lines) * line_height + 2 * padding)

    cv2.rectangle(
        overlay_frame,
        (x0, y0),
        (x0 + panel_width, y0 + panel_height),
        (0, 0, 0),
        -1,
    )

    blended = cv2.addWeighted(overlay_frame, 0.45, frame, 0.55, 0)

    for line_index, line in enumerate(display_lines):
        y = y0 + padding + (line_index + 1) * line_height - 8
        if y > frame.shape[0] - 10:
            break

        color = (255, 255, 255)
        if "FALL" in line:
            color = (0, 0, 255)
        elif "NORMAL" in line:
            color = (0, 255, 0)

        cv2.putText(
            blended,
            line,
            (x0 + padding, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )

    return blended


# Function:
#   play_false_positive_video
# Parameters:
#   model (YOLO): Loaded YOLO model used for realtime per-frame reason calculation.
#   item (FalsePositiveVideo): False-positive metadata record from CSV.
#   video_path (Path): Absolute path to the target video file.
#   current_index (int): 1-based current video index in playback queue.
#   total_count (int): Total number of false-positive videos in playback queue.
# Returns:
#   str: Playback result status in {"completed", "next", "quit", "open_failed"}.
# Description:
#   Plays one false-positive video with realtime reason overlays and keyboard interactions.
def play_false_positive_video(
    model: YOLO,
    item: FalsePositiveVideo,
    video_path: Path,
    current_index: int,
    total_count: int,
) -> str:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        LOGGER.warning("Could not open video: %s", video_path)
        return "open_failed"

    window_name = f"CarePal False Positive {current_index}/{total_count}"

    try:
        fps = get_video_fps(capture)
        frame_delay_ms = get_frame_delay_ms(fps)

        frame_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        if frame_width > 0 and frame_height > 0:
            cv2.resizeWindow(window_name, frame_width, frame_height)

        paused = False
        force_refresh = True
        display_frame: np.ndarray | None = None

        current_streak = 0
        runtime_max_streak = 0

        while True:
            if force_refresh or not paused or display_frame is None:
                ret, frame = capture.read()
                force_refresh = False

                if not ret:
                    break

                analyzed_frame, frame_has_fall, person_reasons = evaluate_frame(model, frame)

                if frame_has_fall:
                    current_streak += 1
                    if current_streak > runtime_max_streak:
                        runtime_max_streak = current_streak
                else:
                    current_streak = 0

                threshold = item.streak_threshold if item.streak_threshold > 0 else DEFAULT_STREAK_THRESHOLD
                status_lines = [
                    f"Video {current_index}/{total_count}: {item.video_name}",
                    f"GT={item.ground_truth_fall}  Pred={item.predicted_fall}",
                    f"CSV max_streak={item.max_fall_streak}  threshold={threshold}",
                    f"Runtime streak={runtime_max_streak}/{threshold}",
                    "Keys: q quit | n next | space pause | left/right seek 3s",
                ]
                display_frame = draw_overlay(analyzed_frame, status_lines, person_reasons)

            if display_frame is not None:
                cv2.imshow(window_name, display_frame)

            wait_ms = 60 if paused else frame_delay_ms
            key = cv2.waitKeyEx(wait_ms)

            if key < 0:
                continue

            if key in KEY_QUIT:
                return "quit"

            if key in KEY_NEXT:
                return "next"

            if key in KEY_PAUSE:
                paused = not paused
                continue

            if key in KEY_LEFT:
                seek_video_by_seconds(capture, -SEEK_SECONDS, fps)
                paused = True
                current_streak = 0
                force_refresh = True
                continue

            if key in KEY_RIGHT:
                seek_video_by_seconds(capture, SEEK_SECONDS, fps)
                paused = True
                current_streak = 0
                force_refresh = True
                continue

        return "completed"
    finally:
        capture.release()
        try:
            cv2.destroyWindow(window_name)
        except cv2.error:
            pass


# Function:
#   main
# Parameters:
#   None: This is the script entry function and does not accept runtime parameters.
# Returns:
#   None: Executes full false-positive playback workflow and logs summary to console.
# Description:
#   Loads CSV and model config, filters false positives, then plays each video with realtime reasons.
def main() -> None:
    csv_path = PROJECT_ROOT / "output" / "result.csv"
    config_path = PROJECT_ROOT / "config" / "models.json"

    try:
        false_positive_items = load_false_positive_videos(csv_path)
    except (FileNotFoundError, ValueError) as error:
        LOGGER.error("Failed to load false-positive list: %s", error)
        return

    if not false_positive_items:
        LOGGER.info("No false-positive videos found in %s", csv_path)
        return

    try:
        model_config = load_model_config(config_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        LOGGER.error("Failed to load model config: %s", error)
        return

    try:
        model_path = resolve_model_weight_path(PROJECT_ROOT, model_config)
    except FileNotFoundError as error:
        LOGGER.error("Failed to resolve model path: %s", error)
        return

    LOGGER.info("Loading YOLO model from %s", model_path)

    try:
        model = YOLO(str(model_path))
    except Exception as error:  # pragma: no cover - runtime environment dependent
        LOGGER.error("Failed to load YOLO model: %s", error)
        return

    played_count = 0
    skipped_count = 0

    for index, item in enumerate(false_positive_items, start=1):
        absolute_video_path = resolve_dataset_video_path(PROJECT_ROOT, item.video_path)

        if not absolute_video_path.exists():
            LOGGER.warning("Video path does not exist, skip: %s", absolute_video_path)
            skipped_count += 1
            continue

        LOGGER.info("Playing false positive %d/%d: %s", index, len(false_positive_items), item.video_path)
        status = play_false_positive_video(
            model=model,
            item=item,
            video_path=absolute_video_path,
            current_index=index,
            total_count=len(false_positive_items),
        )

        if status == "open_failed":
            skipped_count += 1
            continue

        played_count += 1

        if status == "quit":
            LOGGER.info("Playback stopped by user request.")
            break

    cv2.destroyAllWindows()

    LOGGER.info("Playback summary")
    LOGGER.info("Total false positives in CSV: %d", len(false_positive_items))
    LOGGER.info("Videos played: %d", played_count)
    LOGGER.info("Videos skipped: %d", skipped_count)


if __name__ == "__main__":
    main()
