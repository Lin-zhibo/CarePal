from __future__ import annotations

import json
import logging
import os
import re
import socket
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Dict, cast

import cv2
import numpy as np
from fastapi import FastAPI, File, Header, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from ultralytics import YOLO

from condition import check_fall

ROOT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "config" / "models.json"
FRONTEND_APP_CONFIG_PATH = ROOT_DIR.parent / "src" / "config" / "app.config.js"
ALERT_PROTOCOL_TYPE = "emergency_fall_alert"
ALERT_PROTOCOL_VERSION = "1.0"
ALERT_COOLDOWN_SECONDS = 180
ALERT_LISTENER_PORT = 9001
ALERT_SOCKET_TIMEOUT_SECONDS = 2.5

# Ensure log directory exists
(log_path := ROOT_DIR / "log").mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(log_path / "api_server.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)
_alert_cooldown_lock = threading.Lock()
_alert_state = {"last_alert_timestamp": 0.0}


def read_backend_host_from_frontend_config(config_path: Path) -> str:
    """Read backend host from front-end app config file.

    Args:
        config_path (Path): Absolute path to app.config.js.
            Must point to an existing text file.

    Returns:
        str: Parsed backend host value. Empty string when not found.

    Description:
        Extracts the `host` value from `BACKEND_SERVER` object definition in
        front-end config, so YOLO service can align alert target IP with
        existing server settings.
    """
    if not config_path.exists():
        return ""

    try:
        content = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Failed to read front-end config '%s': %s", config_path, exc)
        return ""

    backend_server_match = re.search(
        r"BACKEND_SERVER\s*=\s*Object\.freeze\(\s*\{(?P<body>[\s\S]*?)\}\s*\)",
        content,
    )
    if not backend_server_match:
        return ""

    host_match = re.search(r"host\s*:\s*['\"](?P<host>[^'\"]+)['\"]", backend_server_match.group("body"))
    if not host_match:
        return ""

    return host_match.group("host").strip()


def resolve_alert_listener_host() -> str:
    """Resolve alert listener host using env override then front-end config.

    Args:
        None.

    Returns:
        str: Target host used for TCP alert dispatch.

    Description:
        Uses `ALERT_LISTENER_HOST` environment variable as highest priority.
        Falls back to front-end `src/config/app.config.js` backend host.
        Defaults to 127.0.0.1 when both are unavailable.
    """
    env_host = os.getenv("ALERT_LISTENER_HOST", "").strip()
    if env_host:
        return env_host

    config_host = read_backend_host_from_frontend_config(FRONTEND_APP_CONFIG_PATH)
    if config_host:
        return config_host

    return "127.0.0.1"


def extract_bearer_token(authorization_header: str | None) -> str:
    """Extract JWT token from Authorization header value.

    Args:
        authorization_header (str | None): Raw Authorization header.
            Valid format is `Bearer <token>`.

    Returns:
        str: JWT token string when valid, otherwise empty string.

    Description:
        Parses and validates bearer token syntax for alert protocol usage.
    """
    if not authorization_header:
        return ""

    header = authorization_header.strip()
    if not header.lower().startswith("bearer "):
        return ""

    token = header[7:].strip()
    return token


def reserve_alert_slot(now_timestamp: float) -> tuple[bool, float]:
    """Reserve alert sending slot with global cooldown protection.

    Args:
        now_timestamp (float): Current UNIX timestamp in seconds.
            Must be a non-negative float value.

    Returns:
        tuple[bool, float]:
            - bool: Whether alert sending is allowed now.
            - float: Remaining cooldown seconds if blocked, otherwise 0.0.

    Description:
        Applies a process-level cooldown guard. Once an alert is accepted,
        subsequent alerts are blocked within 180 seconds.
    """
    with _alert_cooldown_lock:
        elapsed = now_timestamp - float(_alert_state["last_alert_timestamp"])
        if elapsed < ALERT_COOLDOWN_SECONDS:
            return False, ALERT_COOLDOWN_SECONDS - elapsed

        _alert_state["last_alert_timestamp"] = now_timestamp
        return True, 0.0


def build_alert_payload(token: str, condition: str, fall_count: int, person_count: int) -> Dict[str, Any]:
    """Build emergency fall alert payload for TCP protocol.

    Args:
        token (str): JWT bearer token string. Must be non-empty.
        condition (str): First matched fall condition message.
            Empty string is allowed.
        fall_count (int): Number of detected fall persons in current frame.
            Must be >= 0.
        person_count (int): Number of detected persons in current frame.
            Must be >= 0.

    Returns:
        Dict[str, Any]: JSON-serializable payload for alert listener.

    Description:
        Creates protocol-compliant JSON containing mandatory fields
        (`type`, `version`, `token`) and useful context for server processing.
    """
    return {
        "type": ALERT_PROTOCOL_TYPE,
        "version": ALERT_PROTOCOL_VERSION,
        "token": token,
        "timestamp": int(time.time()),
        "condition": condition,
        "fall_count": int(max(0, fall_count)),
        "person_count": int(max(0, person_count)),
    }


def send_emergency_alert_tcp(payload: Dict[str, Any], host: str, port: int) -> None:
    """Send emergency payload to listener through TCP.

    Args:
        payload (Dict[str, Any]): Alert payload dictionary.
            Must be JSON serializable.
        host (str): Target listener host/IP.
            Must be a reachable TCP host string.
        port (int): Target listener port.
            Must be in range 1-65535.

    Returns:
        None: Sends data and writes logs.

    Description:
        Serializes payload as UTF-8 JSON bytes and sends a single TCP message
        to the configured listener endpoint.
    """
    try:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        with socket.create_connection((host, port), timeout=ALERT_SOCKET_TIMEOUT_SECONDS) as sock:
            sock.sendall(raw)
        logger.info("Emergency alert sent to %s:%s", host, port)
    except (OSError, ValueError, TypeError) as exc:
        logger.error("Failed to send emergency alert to %s:%s - %s", host, port, exc)


def trigger_fall_alert_if_needed(token: str, condition: str, fall_count: int, person_count: int) -> None:
    """Trigger TCP fall alert with cooldown and non-blocking dispatch.

    Args:
        token (str): JWT token extracted from request Authorization header.
            Must be non-empty to send alert.
        condition (str): Fall condition message from detector.
            Empty string is allowed.
        fall_count (int): Count of fall persons in current frame.
            Must be >= 0.
        person_count (int): Count of detected persons in current frame.
            Must be >= 0.

    Returns:
        None: Schedules TCP send or logs skip reason.

    Description:
        Validates token presence, checks 180-second global cooldown, then
        starts a daemon thread to send alert without blocking API response.
    """
    if not token:
        logger.warning("Fall detected but Authorization token is missing; alert skipped")
        return

    allowed, remaining = reserve_alert_slot(time.time())
    if not allowed:
        logger.info("Fall alert skipped by cooldown, %.1f seconds remaining", remaining)
        return

    payload = build_alert_payload(token, condition, fall_count, person_count)
    thread = threading.Thread(
        target=send_emergency_alert_tcp,
        args=(payload, ALERT_LISTENER_HOST, ALERT_LISTENER_PORT),
        daemon=True,
    )
    thread.start()


ALERT_LISTENER_HOST = resolve_alert_listener_host()
logger.info(
    "Emergency alert listener target: %s:%s, cooldown=%ss",
    ALERT_LISTENER_HOST,
    ALERT_LISTENER_PORT,
    ALERT_COOLDOWN_SECONDS,
)


def load_model_path() -> Path:
    """Load model path with auto-download support.

    Searches multiple candidate paths. If model is not found,
    triggers automatic download via ultralytics and saves to models directory.

    Returns:
        Path: Resolved path to the model file.

    Raises:
        FileNotFoundError: If config file is missing or download fails.
        ValueError: If config is missing required 'model' field.
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Model config not found: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    model_name = str(cfg.get("model", "")).strip()
    models_dir = str(cfg.get("models_dir", "models")).strip() or "models"
    if not model_name:
        raise ValueError("config/models.json missing 'model'")

    candidates = []
    raw = Path(model_name)
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append((ROOT_DIR / raw).resolve())
        candidates.append((ROOT_DIR / models_dir / raw).resolve())
        candidates.append((ROOT_DIR / "models" / raw.name).resolve())
        # Support project-root model directory, e.g. E:/desktop/project/carepal/models
        candidates.append((ROOT_DIR.parent / "models" / raw.name).resolve())
        candidates.append((ROOT_DIR.parent / raw).resolve())

    logger.info("Searching for model '%s' in %d candidate paths...", model_name, len(candidates))
    for path in candidates:
        logger.info("  Checking: %s", path)
        if path.exists():
            logger.info("Model found: %s", path)
            return path

    # Model not found, trigger auto-download
    logger.warning("Model not found, triggering auto-download for '%s'...", model_name)
    target_dir = ROOT_DIR / models_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / model_name

    try:
        # YOLO(model_name) triggers ultralytics to download from official source
        logger.info("Downloading model (this may take a while)...")
        temp_model = YOLO(model_name)
        resolved_ckpt = Path(str(getattr(temp_model, "ckpt_path", str(target_path)))).expanduser()

        if resolved_ckpt.exists() and resolved_ckpt.resolve() != target_path.resolve():
            shutil.move(str(resolved_ckpt), str(target_path))
            logger.info("Model downloaded and saved to: %s", target_path)
        elif not target_path.exists():
            # If move didn't work, copy as fallback
            shutil.copy2(str(resolved_ckpt), str(target_path))
            logger.info("Model downloaded and copied to: %s", target_path)

        if not target_path.exists():
            raise FileNotFoundError(f"Failed to download model to: {target_path}")

        return target_path
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to download model: %s", exc)
        raise FileNotFoundError(f"Model file not found and auto-download failed: {exc}") from exc


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    """Decode raw image bytes into OpenCV BGR frame.

    Args:
        image_bytes (bytes): Raw binary content of an encoded image.
            Must be non-empty bytes for a valid image format.

    Returns:
        np.ndarray: Decoded BGR frame array.

    Description:
        Uses OpenCV decoder to convert uploaded bytes into model-ready frame.
    """
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    cv2_module = cast(Any, cv2)
    decode_candidate = getattr(cv2_module, "imdecode", None)
    imread_color_flag = getattr(cv2_module, "IMREAD_COLOR", 1)
    if decode_candidate is None:
        raise RuntimeError("OpenCV decoder is unavailable")

    decode_callable = cast(Any, decode_candidate)
    frame = decode_callable(array, int(imread_color_flag))
    if frame is None:
        raise ValueError("Invalid image bytes")
    if not isinstance(frame, np.ndarray):
        raise ValueError("Decoded frame is not ndarray")
    return frame


app = FastAPI(title="CarePal YOLO Fall Detection API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("Loading YOLO model...")
MODEL_PATH = load_model_path()
logger.info("YOLO model loaded successfully from: %s", MODEL_PATH)
MODEL = YOLO(str(MODEL_PATH))


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "service": "carepal-yolo"}


@app.post("/detect/frame")
async def detect_frame(
    image: UploadFile = File(...),
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """Detect fall from one image frame and return detection result.

    Args:
        image (UploadFile): Uploaded frame file under form-data field `image`.
            Must be a decodable image binary.
        authorization (str | None): HTTP Authorization header value.
            Expected format is `Bearer <jwt>`.

    Returns:
        JSONResponse: Detection output with fall flags, counts, and person boxes.

    Description:
        Performs YOLO inference on the provided frame. When any fall is
        detected, it triggers a TCP emergency alert with global cooldown.
    """
    try:
        content = await image.read()
        if not content:
            return JSONResponse(status_code=400, content={"message": "Empty image"})

        frame = decode_image_bytes(content)
        results = MODEL(frame, verbose=False)
        result = results[0]

        has_fall = False
        condition = ""
        person_count = 0
        fall_count = 0
        persons = []

        if result.boxes is not None:
            person_count = int(len(result.boxes))

        if result.keypoints is not None and result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            keypoints = result.keypoints.data.cpu().numpy()
            for bbox, kp in zip(boxes, keypoints):
                is_fall, msg = check_fall(kp, bbox)
                
                persons.append({
                    "bbox": [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
                    "is_fall": bool(is_fall),
                    "status": msg if msg else "Normal"
                })

                if is_fall:
                    has_fall = True
                    fall_count += 1
                    if not condition:
                        condition = msg

        if has_fall:
            token = extract_bearer_token(authorization)
            trigger_fall_alert_if_needed(
                token=token,
                condition=condition,
                fall_count=fall_count,
                person_count=person_count,
            )

        return JSONResponse(
            status_code=200,
            content={
                "has_fall": has_fall,
                "condition": condition,
                "person_count": person_count,
                "fall_count": fall_count,
                "persons": persons,
            },
        )
    except (ValueError, RuntimeError, TypeError, OSError) as exc:
        return JSONResponse(status_code=500, content={"message": str(exc)})


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting CarePal YOLO API server on http://0.0.0.0:8010")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8010, reload=False)
