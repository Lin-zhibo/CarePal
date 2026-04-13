from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any, Dict

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from ultralytics import YOLO

from condition import check_fall

ROOT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "config" / "models.json"


def load_model_path() -> Path:
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

    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"Model file not found, candidates: {candidates}")


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Invalid image bytes")
    return frame


app = FastAPI(title="CarePal YOLO Fall Detection API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL = YOLO(str(load_model_path()))


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "service": "carepal-yolo"}


@app.post("/detect/frame")
async def detect_frame(image: UploadFile = File(...)) -> JSONResponse:
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

        if result.boxes is not None:
            person_count = int(len(result.boxes))

        if result.keypoints is not None and result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            keypoints = result.keypoints.data.cpu().numpy()
            for bbox, kp in zip(boxes, keypoints):
                is_fall, msg = check_fall(kp, bbox)
                if is_fall:
                    has_fall = True
                    fall_count += 1
                    if not condition:
                        condition = msg

        return JSONResponse(
            status_code=200,
            content={
                "has_fall": has_fall,
                "condition": condition,
                "person_count": person_count,
                "fall_count": fall_count,
            },
        )
    except Exception as exc:
        return JSONResponse(status_code=500, content={"message": str(exc)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="0.0.0.0", port=8010, reload=False)
