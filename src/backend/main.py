from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.backend.config import get_backend_settings
from src.backend.db import Base, engine, get_db
from src.backend.deps import get_current_user
from src.backend.models import User
from src.backend.schemas import (
    AuthResponse,
    HealthResponse,
    LoginRequest,
    RegisterRequest,
    TextChatRequest,
    TextChatResponse,
)
from src.backend.services import UserService, VoiceAgentService, build_auth_response


settings = get_backend_settings()
Base.metadata.create_all(bind=engine)
voice_agent_service = VoiceAgentService()

app = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug)


@app.on_event("startup")
def startup_event() -> None:
    os.makedirs("outputs/backend/uploads", exist_ok=True)
    os.makedirs("outputs/backend/reply", exist_ok=True)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name, version=settings.app_version)


@app.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = UserService.register(db, payload.username.strip(), payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    return build_auth_response(user)


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = UserService.login(db, payload.username.strip(), payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return build_auth_response(user)


@app.post("/chat/text", response_model=TextChatResponse)
def chat_text(
    payload: TextChatRequest,
    current_user: User = Depends(get_current_user),
):
    answer = voice_agent_service.text_chat(current_user.username, payload.message)
    return TextChatResponse(answer=answer)


@app.post("/chat/voice")
async def chat_voice(
    audio: UploadFile = File(...),
    with_text: bool = Form(False),
    current_user: User = Depends(get_current_user),
):
    ext = Path(audio.filename or "input.wav").suffix or ".wav"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    input_path = os.path.join("outputs", "backend", "uploads", f"{current_user.username}_{ts}{ext}")
    output_path = os.path.join("outputs", "backend", "reply", f"{current_user.username}_{ts}.mp3")

    os.makedirs(os.path.dirname(input_path), exist_ok=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    content = await audio.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio file")
    with open(input_path, "wb") as f:
        f.write(content)

    try:
        voice_result = voice_agent_service.voice_chat(current_user.username, input_path, output_path)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

    if with_text:
        return {
            "asr_text": voice_result["asr_text"],
            "assistant_text": voice_result["assistant_text"],
            "audio_file_url": f"/chat/voice/file/{Path(output_path).name}",
        }

    return FileResponse(output_path, media_type="audio/mpeg", filename="reply.mp3")


@app.get("/chat/voice/file/{filename}")
def get_voice_file(filename: str, current_user: User = Depends(get_current_user)):
    file_path = os.path.join("outputs", "backend", "reply", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)
