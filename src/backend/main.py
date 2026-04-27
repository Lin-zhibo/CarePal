from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import unicodedata
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
    WeixinLoginRequest,
)
from src.backend.services import EmergencyAlertService, UserService, VoiceAgentService, WeixinAuthService, build_auth_response
from src.OCR_agent.service import OCRMultiAgentService
from src.RAG.dbinit import sync_rag_knowledge_on_startup
from src.voice_agent.rag import SimpleRAGStore


settings = get_backend_settings()

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
rag_store = SimpleRAGStore(settings.rag_db_path, state_db_path=settings.rag_state_db_path)
medication_dedup_db_path = Path("db") / "medication_dedup.db"
_medication_dedup_lock = threading.RLock()
emergency_alert_service = EmergencyAlertService(
    host=settings.alert_listener_host,
    port=settings.alert_listener_port,
    trigger_keyword=settings.alert_trigger_keyword,
    email_subject=settings.alert_email_subject,
    email_body=settings.alert_email_body,
    smtp_host=settings.smtp_host,
    smtp_port=settings.smtp_port,
    smtp_username=settings.smtp_username,
    smtp_password=settings.smtp_password,
    smtp_sender_email=settings.smtp_sender_email,
    smtp_use_tls=settings.smtp_use_tls,
    smtp_use_ssl=settings.smtp_use_ssl,
)


def _ensure_user_contact_columns() -> None:
    # 轻量迁移：老库里若没有紧急联系人字段，启动时补齐。
    inspector = inspect(engine)
    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "emergency_contact_name" not in existing_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN emergency_contact_name VARCHAR(128)"))
    if "emergency_contact_email" not in existing_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN emergency_contact_email VARCHAR(255)"))


def _resolve_alert_target_by_token(token: str) -> dict[str, str | None] | None:
    # 从 token 解析用户，再查到其紧急联系人信息。
    if not token:
        return None

    db = SessionLocal()
    try:
        from jose import JWTError, jwt

        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
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


def _infer_audio_ext(filename: str | None, content_type: str | None, content: bytes) -> str:
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


def _normalize_medication_record(record: dict) -> str:
    def _nfkc(text: str) -> str:
        return unicodedata.normalize("NFKC", text)

    def _canon(value: str) -> str:
        text = _nfkc(str(value or "").strip().lower())
        text = text.replace("每天", "每日").replace("一日", "每日")
        text = text.replace("次/天", "次/日").replace("次/每日", "次/日")
        text = text.replace("每次", "")
        text = text.replace("温开水", "温水")
        text = text.replace("送服", "服用")
        text = text.replace("（", "(").replace("）", ")")
        text = text.replace("。", ".").replace("；", ";").replace("：", ":").replace("，", ",")
        text = re.sub(r"(?<=\d)\.0+(?=\D|$)", "", text)
        text = re.sub(r"(?<=\d)\.([1-9])0+(?=\D|$)", r".\1", text)
        text = re.sub(r"\((\d+(?:\.\d+)?)g/片\)", r"(\1g)", text)
        text = re.sub(r"\b每?日(\d+)次\b", r"\1次/日", text)
        text = re.sub(r"\b(\d+)次每?日\b", r"\1次/日", text)
        text = re.sub(r"\b(\d+)次/每日\b", r"\1次/日", text)
        text = re.sub(r"\b(\d+)次/天\b", r"\1次/日", text)
        text = re.sub(r"\b(\d+)次/日\b", r"\1次/日", text)
        text = re.sub(r"\s*([,;:.])\s*", r"\1", text)
        text = re.sub(r"\s+", "", text)
        return text

    normalized = {
        "药品名": _canon(record.get("药品名", "")),
        "单次剂量": _canon(record.get("单次剂量", "")),
        "每日频次": _canon(record.get("每日频次", "")),
        "服药时间": _canon(record.get("服药时间", "")),
    }
    compact = "|".join(f"{k}:{normalized[k]}" for k in sorted(normalized.keys()))
    compact = re.sub(r"\s+", " ", compact).strip()
    return compact


def _init_medication_dedup_schema() -> None:
    medication_dedup_db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(medication_dedup_db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS medication_signature_state (
                signature TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _is_medication_signature_known(signature: str) -> bool:
    if not signature:
        return False
    with _medication_dedup_lock:
        with sqlite3.connect(str(medication_dedup_db_path)) as conn:
            row = conn.execute(
                "SELECT 1 FROM medication_signature_state WHERE signature = ? LIMIT 1",
                (signature,),
            ).fetchone()
            return row is not None


def _record_medication_signature(signature: str, source: str) -> None:
    with _medication_dedup_lock:
        with sqlite3.connect(str(medication_dedup_db_path)) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO medication_signature_state(signature, created_at, source) VALUES (?, ?, ?)",
                (signature, datetime.now().isoformat(), source),
            )
            conn.commit()


def _ingest_medication_json_to_rag(payload: dict | None, owner: str) -> int:
    if not settings.rag_enabled:
        return 0

    if not payload or not isinstance(payload, dict):
        return 0

    medicines = payload.get("medicines")
    if not isinstance(medicines, list):
        return 0

    unique_docs: list[str] = []
    pending_signatures: set[str] = set()
    for med in medicines:
        if not isinstance(med, dict):
            continue
        signature = _normalize_medication_record(med)
        if not signature:
            continue
        if signature in pending_signatures:
            continue
        if _is_medication_signature_known(signature):
            continue
        pending_signatures.add(signature)
        normalized_doc = {
            "药品名": str(med.get("药品名", "")).strip(),
            "单次剂量": str(med.get("单次剂量", "")).strip(),
            "每日频次": str(med.get("每日频次", "")).strip(),
            "服药时间": str(med.get("服药时间", "")).strip(),
            "注意事项": str(med.get("注意事项", "")).strip(),
        }
        doc = json.dumps(normalized_doc, ensure_ascii=False, separators=(",", ":"))
        unique_docs.append(doc)

    if not unique_docs:
        return 0

    source = f"ocr_medication_dynamic::{owner}::{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    rag_store.add_documents(unique_docs, source=source)
    for signature in pending_signatures:
        _record_medication_signature(signature, source)
    return len(unique_docs)

app = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug)


@app.on_event("startup")
def startup_event() -> None:
    logger.info("Starting up application...")
    _ensure_user_contact_columns()
    _init_medication_dedup_schema()
    os.makedirs("outputs/backend/uploads", exist_ok=True)
    os.makedirs("outputs/backend/reply", exist_ok=True)
    emergency_alert_service.start_listener(_resolve_alert_target_by_token)
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
    return HealthResponse(status="ok", app=settings.app_name, version=settings.app_version)


@app.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    logger.info("Registering new user: %s", payload.username)
    user = UserService.register(
        db,
        payload.username.strip(),
        payload.password,
        payload.emergency_contact_name.strip(),
        payload.emergency_contact_email.strip(),
    )
    if user is None:
        logger.warning("Registration failed: Username %s already exists", payload.username)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    logger.info("User registered successfully: %s", payload.username)
    return build_auth_response(user)


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    logger.info("User login attempt: %s", payload.username)
    user = UserService.login(db, payload.username.strip(), payload.password)
    if user is None:
        logger.warning("Login failed for user: %s", payload.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    logger.info("User logged in successfully: %s", payload.username)
    return build_auth_response(user)


@app.post("/auth/login_weixin", response_model=AuthResponse)
def login_weixin(payload: WeixinLoginRequest, db: Session = Depends(get_db)):
    logger.info("Weixin login attempt received")
    try:
        session_info = WeixinAuthService.exchange_code_for_session(
            code=payload.code.strip(),
            app_id=settings.weixin_app_id,
            app_secret=settings.weixin_app_secret,
            endpoint=settings.weixin_jscode2session_url,
        )
    except RuntimeError as e:
        logger.warning("Weixin login exchange failed: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    openid = session_info["openid"]
    session_key = session_info["session_key"]

    user = UserService.login(db, openid, session_key)
    if user is None:
        user = UserService.register_weixin_user(db, openid, session_key)
        user = UserService.login(db, openid, session_key)

    if user is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="微信登录失败，请重试")

    logger.info("Weixin user logged in successfully: %s", openid)
    return build_auth_response(user)


@app.get("/auth/emergency-contact", response_model=EmergencyContactInfoResponse)
def get_emergency_contact(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    info = UserService.get_emergency_contact(db, auth.user.username)
    if info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return EmergencyContactInfoResponse(**info)


@app.post("/chat/text", response_model=TextChatResponse)
async def chat_text(
    payload: TextChatRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    logger.info("Handling /chat/text request for user: %s (Prompt template: %s)", auth.user.username, payload.prompt)
    try:
        prompt_text = resolve_prompt(payload.prompt)
    except ValueError as e:
        logger.error("Invalid prompt template ID: %s", payload.prompt)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    logger.info("Calling voice_agent_service.text_chat for user %s", auth.user.username)
    result = await run_in_threadpool(
        voice_agent_service.text_chat,
        auth.token,
        auth.user.username,
        payload.message,
        payload.prompt,
        prompt_text,
        payload.with_audio,
    )
    logger.info("Voice agent text_chat completed for user %s", auth.user.username)
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
    logger.info("Handling /chat/voice request for user: %s (Prompt template: %s)", auth.user.username, prompt)
    content = await audio.read()
    if not content:
        logger.warning("Empty audio upload from user %s", auth.user.username)
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
        logger.info("Calling voice_agent_service.voice_chat for user %s", auth.user.username)
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
        logger.info("Voice chat completed for user %s", auth.user.username)
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
    with_medication_extraction: bool = Form(True),
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
        result = await run_in_threadpool(ocr_service.analyze_images, auth.token, saved_paths, prompt)
        logger.info("OCR analysis completed for user %s", auth.user.username)
    except Exception as e:
        logger.exception("/ocr/analyze failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

    ocr_audio_url = None
    medication_json = None
    rag_ingested_count = None

    if with_medication_extraction:
        try:
            extraction = await run_in_threadpool(ocr_service.extract_medication_info, auth.token, saved_paths, None)
            medication_json = extraction.medication_json
            rag_ingested_count = _ingest_medication_json_to_rag(medication_json, auth.user.username)
        except Exception as e:
            logger.warning("/ocr/analyze medication extraction failed: %s", e)

    if with_audio and result.text:
        audio_path = os.path.join("outputs", "backend", "reply", f"ocr_{auth.user.username}_{ts}.mp3")
        try:
            await run_in_threadpool(voice_agent_service.pipeline.tts.synthesize_to_file, result.text, audio_path)
            ocr_audio_url = f"/chat/voice/file/{Path(audio_path).name}"
        except Exception as e:
            logger.warning("/ocr/analyze tts failed, fallback to text-only response: %s", e)

    return OCRAnalyzeResponse(
        text=result.text,
        audio_file_url=ocr_audio_url,
        medication_json=medication_json,
        rag_ingested_count=rag_ingested_count,
    )
