from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.backend.config import get_backend_settings
from src.backend.db import Base, engine, get_db
from src.backend.deps import AuthContext, get_auth_context, get_current_user
from src.backend.models import User
from src.backend.prompt_templates import resolve_prompt
from src.backend.schemas import (
    AuthResponse,
    HealthResponse,
    LoginRequest,
    RegisterRequest,
    TextChatRequest,
    TextChatResponse,
    VoiceChatMetaResponse,
    OCRAnalyzeResponse,
)
from src.backend.services import UserService, VoiceAgentService, build_auth_response
from src.OCR_agent.service import OCRMultiAgentService


settings = get_backend_settings()
Base.metadata.create_all(bind=engine)
voice_agent_service = VoiceAgentService()
ocr_service = OCRMultiAgentService()
logger = logging.getLogger(__name__)


def _infer_audio_ext(filename: str | None, content_type: str | None, content: bytes) -> str:
    if filename:
        suffix = Path(filename).suffix.lower()
        if suffix in {".wav", ".mp3"}:
            return suffix

    ct = (content_type or "").lower()
    if ct in {"audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave"}:
        return ".wav"
    if ct in {"audio/mpeg", "audio/mp3"}:
        return ".mp3"

    # magic bytes fallback
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WAVE":
        return ".wav"
    if len(content) >= 3 and content[:3] == b"ID3":
        return ".mp3"
    if len(content) >= 2 and content[0] == 0xFF and (content[1] & 0xE0) == 0xE0:
        return ".mp3"

    return ""

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
async def chat_text(
    payload: TextChatRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    try:
        prompt_text = resolve_prompt(payload.prompt)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    result = await run_in_threadpool(
        voice_agent_service.text_chat,
        auth.token,
        auth.user.username,
        payload.message,
        payload.prompt,
        prompt_text,
        payload.with_audio,
    )
    audio_file_url = None
    if payload.with_audio and result.get("audio_output_path"):
        audio_file_url = f"/chat/voice/file/{Path(result['audio_output_path']).name}"

    if payload.with_text:
        return TextChatResponse(
            answer=result.get("assistant_text"),
            asr_text=None,
            assistant_text=result.get("assistant_text"),
            assistant_payload=result.get("assistant_payload"),
            audio_file_url=audio_file_url,
        )

    return TextChatResponse(
        answer=None,
        asr_text=None,
        assistant_text=None,
        assistant_payload=result.get("assistant_payload"),
        audio_file_url=audio_file_url,
    )


@app.post("/chat/voice")
async def chat_voice(
    audio: UploadFile = File(...),
    prompt: int | None = Form(None),
    with_text: bool = Form(False),
    with_audio: bool = Form(True),
    auth: AuthContext = Depends(get_auth_context),
):
    content = await audio.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio file")

    ext = _infer_audio_ext(audio.filename, audio.content_type, content)
    if not ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported audio format. only wav(raw) or mp3(lame) is supported",
        )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    input_path = os.path.join("outputs", "backend", "uploads", f"{auth.user.username}_{ts}{ext}")
    output_path = os.path.join("outputs", "backend", "reply", f"{auth.user.username}_{ts}.mp3")

    os.makedirs(os.path.dirname(input_path), exist_ok=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(input_path, "wb") as f:
        f.write(content)

    try:
        prompt_text = resolve_prompt(prompt)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    try:
        voice_result = await run_in_threadpool(
            voice_agent_service.voice_chat,
            auth.token,
            auth.user.username,
            input_path,
            output_path,
            prompt,
            prompt_text,
            with_audio,
        )
    except (RuntimeError, ValueError) as e:
        logger.warning("/chat/voice bad request: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception("/chat/voice failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

    generated_audio_path = voice_result.get("audio_output_path")
    generated_audio_url = None
    if generated_audio_path:
        generated_audio_url = f"/chat/voice/file/{Path(generated_audio_path).name}"

    # 两种情况统一走JSON返回：
    # 1) 前端显式要求 with_audio=false
    # 2) 业务策略决定本轮不生成音频（如 prompt=1 且 intent=schedule_edit）
    if (not with_audio) or (not generated_audio_path):
        return VoiceChatMetaResponse(
            asr_text=voice_result.get("asr_text") if with_text else None,
            assistant_text=voice_result.get("assistant_text") if with_text else None,
            assistant_payload=voice_result.get("assistant_payload"),
            audio_file_url=generated_audio_url,
        )

    if with_text:
        return VoiceChatMetaResponse(
            asr_text=voice_result.get("asr_text"),
            assistant_text=voice_result.get("assistant_text"),
            assistant_payload=voice_result.get("assistant_payload"),
            audio_file_url=generated_audio_url,
        )

    return FileResponse(generated_audio_path, media_type="audio/mpeg", filename="reply.mp3")


@app.get("/chat/voice/file/{filename}")
def get_voice_file(filename: str, current_user: User = Depends(get_current_user)):
    file_path = os.path.join("outputs", "backend", "reply", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)


@app.post("/ocr/analyze", response_model=OCRAnalyzeResponse)
async def ocr_analyze(
    images: list[UploadFile] = File(...),
    prompt: str | None = Form(None),
    with_audio: bool = Form(False),
    auth: AuthContext = Depends(get_auth_context),
):
    if not images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No image files uploaded")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    upload_dir = os.path.join("outputs", "backend", "ocr", "uploads", f"{auth.user.username}_{ts}")
    os.makedirs(upload_dir, exist_ok=True)

    saved_paths: list[Path] = []
    for i, image in enumerate(images, start=1):
        content = await image.read()
        if not content:
            continue
        ext = Path(image.filename or f"img_{i}.jpg").suffix.lower() or ".jpg"
        if ext not in {".png", ".jpg", ".jpeg"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported image type: {ext}")
        file_path = Path(upload_dir) / f"img_{i}{ext}"
        file_path.write_bytes(content)
        saved_paths.append(file_path)

    if not saved_paths:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All uploaded images are empty")

    try:
        result = await run_in_threadpool(ocr_service.analyze_images, auth.token, saved_paths, prompt)
    except Exception as e:
        logger.exception("/ocr/analyze failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

    ocr_audio_url = None
    if with_audio and result.text:
        audio_path = os.path.join("outputs", "backend", "reply", f"ocr_{auth.user.username}_{ts}.mp3")
        try:
            await run_in_threadpool(voice_agent_service.pipeline.tts.synthesize_to_file, result.text, audio_path)
            ocr_audio_url = f"/chat/voice/file/{Path(audio_path).name}"
        except Exception as e:
            logger.exception("/ocr/analyze tts failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OCR文本转语音失败: {e}") from e

    return OCRAnalyzeResponse(text=result.text, audio_file_url=ocr_audio_url)
