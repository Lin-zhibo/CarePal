from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from src.backend.config import get_backend_settings
from src.backend.db import Base, SessionLocal, engine, get_db
from src.backend.deps import AuthContext, get_auth_context, get_current_user
from src.backend.models import User
from src.backend.prompt_templates import resolve_prompt
from src.backend.schemas import (
    AuthResponse,
    EmergencyContactInfoResponse,
    HealthResponse,
    LoginRequest,
    OCRAnalyzeResponse,
    RegisterRequest,
    TextChatRequest,
    TextChatResponse,
    VoiceChatMetaResponse,
)
from src.backend.services import EmergencyAlertService, UserService, VoiceAgentService, build_auth_response
from src.OCR_agent.service import OCRMultiAgentService
from src.RAG.dbinit import sync_rag_knowledge_on_startup


cfg01 = get_backend_settings()

os.makedirs("log", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("log/log.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("Initializing database...")
Base.metadata.create_all(bind=engine)
logger.info("Database initialized.")

# 这些 service 在进程启动时初始化，全局复用。
voice_agent_service = VoiceAgentService()
ocr_service = OCRMultiAgentService()
emergency_alert_service = EmergencyAlertService(
    host=cfg01.alert_listener_host,
    port=cfg01.alert_listener_port,
    trigger_keyword=cfg01.alert_trigger_keyword,
    email_subject=cfg01.alert_email_subject,
    email_body=cfg01.alert_email_body,
    smtp_host=cfg01.smtp_host,
    smtp_port=cfg01.smtp_port,
    smtp_username=cfg01.smtp_username,
    smtp_password=cfg01.smtp_password,
    smtp_sender_email=cfg01.smtp_sender_email,
    smtp_use_tls=cfg01.smtp_use_tls,
    smtp_use_ssl=cfg01.smtp_use_ssl,
)


def _m03() -> None:
    # 轻量迁移：老库里若没有紧急联系人字段，启动时补齐。
    inspector = inspect(engine)
    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "emergency_contact_name" not in existing_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN emergency_contact_name VARCHAR(128)"))
    if "emergency_contact_email" not in existing_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN emergency_contact_email VARCHAR(255)"))


def _m07(token: str) -> dict[str, str | None] | None:
    # 从 token 解析用户，再查到其紧急联系人信息。
    if not token:
        return None

    db = SessionLocal()
    try:
        from jose import JWTError, jwt

        try:
            payload = jwt.decode(token, cfg01.jwt_secret_key, algorithms=[cfg01.jwt_algorithm])
            username = payload.get("sub")
        except JWTError:
            return None

        if not username:
            return None

        user = db.query(User).filter(User.username == username).first()
        if user is None:
            return None

        return {
            "username": user.username,
            "emergency_contact_name": user.emergency_contact_name,
            "emergency_contact_email": user.emergency_contact_email,
        }
    finally:
        db.close()


def _m11(filename: str | None, content_type: str | None, content: bytes) -> str:
    # 文件后缀 + content-type + 魔数三重判断，尽量识别真实音频格式。
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

app = FastAPI(title=cfg01.app_name, version=cfg01.app_version, debug=cfg01.debug)


@app.on_event("startup")
def startup_event() -> None:
    logger.info("Starting up application...")
    _m03()
    os.makedirs("outputs/backend/uploads", exist_ok=True)
    os.makedirs("outputs/backend/reply", exist_ok=True)
    emergency_alert_service.start_listener(_m07)
    try:
        # 服务启动时同步 RAG，避免知识库与本地文件不一致。
        logger.info("Syncing RAG knowledge...")
        sync_rag_knowledge_on_startup()
        logger.info("RAG knowledge sync completed successfully.")
    except Exception as e:
        logger.exception("Failed to sync RAG knowledge on startup.")
        raise


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=cfg01.app_name, version=cfg01.app_version)


@app.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    logger.info("Registering new user: %s", payload.username)
    u01 = UserService.register(
        db,
        payload.username.strip(),
        payload.password,
        payload.emergency_contact_name.strip(),
        payload.emergency_contact_email.strip(),
    )
    if u01 is None:
        logger.warning("Registration failed: Username %s already exists", payload.username)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    logger.info("User registered successfully: %s", payload.username)
    return build_auth_response(u01)


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    logger.info("User login attempt: %s", payload.username)
    u01 = UserService.login(db, payload.username.strip(), payload.password)
    if u01 is None:
        logger.warning("Login failed for user: %s", payload.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    logger.info("User logged in successfully: %s", payload.username)
    return build_auth_response(u01)


@app.get("/auth/emergency-contact", response_model=EmergencyContactInfoResponse)
def get_emergency_contact(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    i01 = UserService.get_emergency_contact(db, auth.user.username)
    if i01 is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return EmergencyContactInfoResponse(**i01)


@app.post("/chat/text", response_model=TextChatResponse)
async def chat_text(
    payload: TextChatRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    logger.info("Handling /chat/text request for user: %s (Prompt template: %s)", auth.user.username, payload.prompt)
    try:
        p01 = resolve_prompt(payload.prompt)
    except ValueError as e:
        logger.error("Invalid prompt template ID: %s", payload.prompt)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    logger.info("Calling voice_agent_service.text_chat for user %s", auth.user.username)
    r01 = await run_in_threadpool(
        voice_agent_service.text_chat,
        auth.token,
        auth.user.username,
        payload.message,
        payload.prompt,
        p01,
        payload.with_audio,
    )
    logger.info("Voice agent text_chat completed for user %s", auth.user.username)
    audio_file_url = None
    if payload.with_audio and r01.get("audio_output_path"):
        audio_file_url = f"/chat/voice/file/{Path(r01['audio_output_path']).name}"

    if payload.with_text:
        return TextChatResponse(
            answer=r01.get("assistant_text"),
            asr_text=None,
            assistant_text=r01.get("assistant_text"),
            assistant_payload=r01.get("assistant_payload"),
            audio_file_url=audio_file_url,
        )

    return TextChatResponse(
        answer=None,
        asr_text=None,
        assistant_text=None,
        assistant_payload=r01.get("assistant_payload"),
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
    logger.info("Handling /chat/voice request for user: %s (Prompt template: %s)", auth.user.username, prompt)
    content = await audio.read()
    if not content:
        logger.warning("Empty audio upload from user %s", auth.user.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio file")

    ext = _m11(audio.filename, audio.content_type, content)
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
        p01 = resolve_prompt(prompt)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    try:
        logger.info("Calling voice_agent_service.voice_chat for user %s", auth.user.username)
        r01 = await run_in_threadpool(
            voice_agent_service.voice_chat,
            auth.token,
            auth.user.username,
            input_path,
            output_path,
            prompt,
            p01,
            with_audio,
        )
        logger.info("Voice chat completed for user %s", auth.user.username)
    except (RuntimeError, ValueError) as e:
        logger.warning("/chat/voice bad request: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception("/chat/voice failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

    generated_audio_path = r01.get("audio_output_path")
    generated_audio_url = None
    if generated_audio_path:
        generated_audio_url = f"/chat/voice/file/{Path(generated_audio_path).name}"

    # 两种情况统一走JSON返回：
    # 1) 前端显式要求 with_audio=false
    # 2) 业务策略决定本轮不生成音频（如 prompt=1 且 intent=schedule_edit）
    if (not with_audio) or (not generated_audio_path):
        return VoiceChatMetaResponse(
            asr_text=r01.get("asr_text") if with_text else None,
            assistant_text=r01.get("assistant_text") if with_text else None,
            assistant_payload=r01.get("assistant_payload"),
            audio_file_url=generated_audio_url,
        )

    if with_text:
        return VoiceChatMetaResponse(
            asr_text=r01.get("asr_text"),
            assistant_text=r01.get("assistant_text"),
            assistant_payload=r01.get("assistant_payload"),
            audio_file_url=generated_audio_url,
        )

    return FileResponse(generated_audio_path, media_type="audio/mpeg", filename="reply.mp3")


@app.get("/chat/voice/file/{filename}")
def get_voice_file(filename: str, current_user: User = Depends(get_current_user)):
    p01 = os.path.join("outputs", "backend", "reply", filename)
    if not os.path.exists(p01):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")
    return FileResponse(p01, media_type="audio/mpeg", filename=filename)


@app.post("/ocr/analyze", response_model=OCRAnalyzeResponse)
async def ocr_analyze(
    images: list[UploadFile] = File(...),
    prompt: str | None = Form(None),
    with_audio: bool = Form(False),
    auth: AuthContext = Depends(get_auth_context),
):
    logger.info("Handling /ocr/analyze request for user: %s (Images count: %d)", auth.user.username, len(images) if images else 0)
    if not images:
        logger.warning("No images uploaded for OCR by user %s", auth.user.username)
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
        logger.warning("All uploaded images were empty for user %s", auth.user.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All uploaded images are empty")

    try:
        logger.info("Calling ocr_service.analyze_images for user %s with %d images", auth.user.username, len(saved_paths))
        r01 = await run_in_threadpool(ocr_service.analyze_images, auth.token, saved_paths, prompt)
        logger.info("OCR analysis completed for user %s", auth.user.username)
    except Exception as e:
        logger.exception("/ocr/analyze failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

    ocr_audio_url = None
    if with_audio and r01.text:
        audio_path = os.path.join("outputs", "backend", "reply", f"ocr_{auth.user.username}_{ts}.mp3")
        try:
            await run_in_threadpool(voice_agent_service.pipeline.tts.synthesize_to_file, r01.text, audio_path)
            ocr_audio_url = f"/chat/voice/file/{Path(audio_path).name}"
        except Exception as e:
            logger.warning("/ocr/analyze tts failed, fallback to text-only response: %s", e)

    return OCRAnalyzeResponse(text=r01.text, audio_file_url=ocr_audio_url)
