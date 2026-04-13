# CarePal-yolo

## Run YOLO API Service

This folder now includes an HTTP API service for the front-end monitor module.

### 1) Install dependencies

pip install fastapi uvicorn ultralytics opencv-python numpy python-multipart

### 2) Start service

cd CarePal-yolo
python api_server.py

Service default address:
- http://127.0.0.1:8010

### 3) API

- GET /health
- POST /detect/frame
  - form-data field name: image
  - returns:
    - has_fall: bool
    - condition: string
    - person_count: int
    - fall_count: int

## Front-end integration

The front-end monitor module calls /detect/frame through Vite proxy /yoloapi in development mode.
