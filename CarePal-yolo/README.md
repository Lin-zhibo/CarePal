# CarePal-yolo

## Run YOLO API Service

This folder now includes an HTTP API service for the front-end monitor module.

### 1) Install dependencies

pip install fastapi uvicorn ultralytics opencv-python numpy python-multipart

### 2) Start service

cd CarePal-yolo
python api_server.py

Service default address:

- `http://127.0.0.1:8010`

### 3) API

- GET /health
- POST /detect/frame
  - form-data field name: image
  - request header: Authorization: Bearer jwt-token (used for emergency alert payload)
  - returns:
    - has_fall: bool
    - condition: string
    - person_count: int
    - fall_count: int

### 4) Emergency alert TCP reporting

When `has_fall=true`, service sends a UTF-8 JSON message to emergency listener.

- listener host priority:
  1. env `ALERT_LISTENER_HOST`
  2. fallback to `src/config/app.config.js` -> `BACKEND_SERVER.host`
  3. fallback to `127.0.0.1`
- listener port: `9001`
- global cooldown: `180s` (3 minutes)

Minimum payload fields:

```json
{
  "type": "emergency_fall_alert",
  "version": "1.0",
  "token": "<jwt-token>"
}
```

Current payload also includes context fields (`timestamp`, `condition`, `fall_count`, `person_count`).

## Front-end integration

The front-end monitor module calls /detect/frame through Vite proxy /yoloapi in development mode.
