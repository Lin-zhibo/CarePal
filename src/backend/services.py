from __future__ import annotations

import json
import logging
import os
import smtplib
import socket
import threading
from datetime import datetime
from email.message import EmailMessage
from typing import Any
from typing import Dict, List

from sqlalchemy.orm import Session

from src.voice_agent.config import get_settings
from src.voice_agent.pipeline import VoicePipeline

from .models import User
from .security import create_access_token, hash_password, verify_password


logger = logging.getLogger(__name__)


class UserService:
    # 账号相关的数据库读写逻辑，和路由层解耦。
    @staticmethod
    def register(
        db: Session,
        username: str,
        password: str,
        emergency_contact_name: str,
        emergency_contact_email: str,
    ):
        exists = db.query(User).filter(User.username == username).first()
        if exists:
            return None
        user = User(
            username=username,
            password_hash=hash_password(password),
            emergency_contact_name=emergency_contact_name,
            emergency_contact_email=emergency_contact_email,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def login(db: Session, username: str, password: str):
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def get_emergency_contact(db: Session, username: str) -> dict[str, str | None] | None:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            return None
        return {
            "emergency_contact_name": user.emergency_contact_name,
            "emergency_contact_email": user.emergency_contact_email,
        }


class EmergencyAlertService:
    # 监听 TCP 告警并发送紧急联系人邮件。
    def __init__(
        self,
        host: str,
        port: int,
        trigger_keyword: str,
        email_subject: str,
        email_body: str,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        smtp_sender_email: str,
        smtp_use_tls: bool,
        smtp_use_ssl: bool,
    ) -> None:
        self.host = host
        self.port = port
        self.trigger_keyword = trigger_keyword
        self.email_subject = email_subject
        self.email_body = email_body
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_sender_email = smtp_sender_email
        self.smtp_use_tls = smtp_use_tls
        self.smtp_use_ssl = smtp_use_ssl

    def start_listener(self, resolve_alert_target_by_token) -> threading.Thread | None:
        if self.port <= 0:
            logger.info("Emergency alert listener is disabled because ALERT_LISTENER_PORT <= 0")
            return None

        thread = threading.Thread(
            target=self._listen_loop,
            args=(resolve_alert_target_by_token,),
            daemon=True,
            name="emergency-alert-listener",
        )
        thread.start()
        logger.info("Emergency alert listener started at %s:%s", self.host, self.port)
        return thread

    @staticmethod
    def _parse_bool(value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return default

    def _parse_listener_payload(self, payload: str) -> dict[str, Any] | None:
        # 兼容两种输入：JSON 报文 / 直接传 token 字符串。
        stripped = payload.strip()
        if not stripped:
            return None

        data: dict[str, Any]
        try:
            parsed = json.loads(stripped)
            data = parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            data = {"token": stripped}

        token = str(data.get("token", "")).strip()
        if not token:
            return None

        message_type = str(data.get("type", "")).strip()
        if message_type and message_type != "emergency_fall_alert":
            return None

        return data

    def _listen_loop(self, resolve_alert_target_by_token) -> None:
        # 常驻循环：单连接读取单条报文，处理完成后关闭连接。
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(5)

        while True:
            conn, addr = server.accept()
            with conn:
                try:
                    data = conn.recv(4096)
                    if not data:
                        continue
                    raw_payload = data.decode("utf-8", errors="ignore")
                    parsed_payload = self._parse_listener_payload(raw_payload)
                    if not parsed_payload:
                        logger.warning("Emergency alert payload is invalid or trigger mismatch from %s", addr)
                        continue

                    token = str(parsed_payload.get("token", "")).strip()
                    alert_target = resolve_alert_target_by_token(token)
                    if not alert_target:
                        logger.warning("Emergency alert ignored because token has no matching user. from=%s", addr)
                        continue

                    self.send_alert_email(alert_target, parsed_payload)
                except Exception as exc:
                    logger.exception("Emergency alert listener failed to handle request from %s: %s", addr, exc)

    def send_alert_email(self, alert_target: dict[str, str | None], payload_overrides: dict[str, Any] | None = None) -> None:
        recipient = (alert_target.get("emergency_contact_email") or "").strip()
        contact_name = (alert_target.get("emergency_contact_name") or "").strip() or "紧急联系人"
        username = (alert_target.get("username") or "").strip() or "该用户"

        if not recipient:
            logger.warning("Emergency alert skipped because recipient email is empty. user=%s", username)
            return

        raw_overrides = payload_overrides or {}
        nested_overrides = raw_overrides.get("smtp_override") if isinstance(raw_overrides, dict) else None
        if isinstance(nested_overrides, dict):
            overrides = {**raw_overrides, **nested_overrides}
        else:
            overrides = raw_overrides

        smtp_host = str(overrides.get("smtp_host", self.smtp_host) or "").strip()
        smtp_port = int(overrides.get("smtp_port", self.smtp_port) or self.smtp_port)
        smtp_username = str(overrides.get("smtp_username", self.smtp_username) or "").strip()
        smtp_password = str(overrides.get("smtp_password", self.smtp_password) or "").strip()
        smtp_sender_email = str(overrides.get("smtp_sender_email", self.smtp_sender_email) or "").strip()
        smtp_use_tls = self._parse_bool(overrides.get("smtp_use_tls"), self.smtp_use_tls)
        smtp_use_ssl = self._parse_bool(overrides.get("smtp_use_ssl"), self.smtp_use_ssl)

        if not smtp_host or not smtp_sender_email:
            logger.warning("Emergency alert skipped because smtp_host or smtp_sender_email is empty")
            return

        message = EmailMessage()
        message["From"] = smtp_sender_email
        message["To"] = recipient
        message["Subject"] = self.email_subject or "CarePal 紧急提醒"
        message_template = self.email_body or "（{contact_name}）你好，你家里的老人（{username}）可能刚才跌倒了，请尽快打电话确认老人情况！！！"
        try:
            message_body = message_template.format(contact_name=contact_name, username=username)
        except Exception:
            message_body = message_template
        message.set_content(message_body)

        if smtp_use_ssl:
            smtp_client = smtplib.SMTP_SSL
        else:
            smtp_client = smtplib.SMTP

        with smtp_client(smtp_host, smtp_port, timeout=20) as server:
            if (not smtp_use_ssl) and smtp_use_tls:
                server.starttls()
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            server.send_message(message)
        logger.info("Emergency alert email sent successfully. user=%s recipient=%s", username, recipient)


class VoiceAgentService:
    # 对 VoicePipeline 做会话级封装，管理历史和并发锁。
    def __init__(self) -> None:
        self.settings = get_settings()
        self.pipeline = VoicePipeline(self.settings)
        self.user_histories: Dict[str, List[Dict[str, str]]] = {}
        self._session_locks: Dict[str, threading.Lock] = {}
        self._manager_lock = threading.RLock()

    def _history(self, user_key: str) -> List[Dict[str, str]]:
        with self._manager_lock:
            if user_key not in self.user_histories:
                self.user_histories[user_key] = []
            return self.user_histories[user_key]

    def _get_session_lock(self, user_key: str) -> threading.Lock:
        with self._manager_lock:
            if user_key not in self._session_locks:
                self._session_locks[user_key] = threading.Lock()
            return self._session_locks[user_key]

    @staticmethod
    def _compress_history_if_needed(history: List[Dict[str, str]]) -> None:
        # 每50轮做一次压缩：保留system + 最近10轮，前40轮做摘要条目
        if not history:
            return
        if history[0].get("role") == "system":
            system = history[0]
            dialog = history[1:]
        else:
            system = None
            dialog = history

        if len(dialog) < 100:
            return

        old_part = dialog[:-20]
        recent_part = dialog[-20:]

        summary_items = []
        for item in old_part:
            role = item.get("role", "user")
            content = item.get("content", "")
            if not content:
                continue
            summary_items.append(f"[{role}] {content[:120]}")

        summary_text = "历史摘要：\n" + "\n".join(summary_items[:120])
        compressed_dialog = [{"role": "assistant", "content": summary_text}] + recent_part

        history.clear()
        if system:
            history.append(system)
        history.extend(compressed_dialog)

    def text_chat(
        self,
        user_key: str,
        username: str,
        message: str,
        prompt_id: int | None = None,
        prompt: str | None = None,
        with_audio: bool = False,
    ) -> dict:
        session_lock = self._get_session_lock(user_key)
        with session_lock:
            history = self._history(user_key)
            self._compress_history_if_needed(history)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            out_path = os.path.join("outputs", "backend", "reply", f"{username}_{ts}.mp3")
            result = self.pipeline.run_from_text(
                user_text=message,
                history=history,
                output_audio_path=None,
                stream_to_console=False,
                system_prompt=prompt,
                enable_tts=False,
            )
            parsed_payload = self._try_parse_json(result.assistant_text)
            tts_text, allow_tts = self._decide_tts_text(prompt_id, result.assistant_text, parsed_payload)
            frontend_text = self._decide_frontend_text(prompt_id, result.assistant_text, parsed_payload)

            audio_output_path = None
            if with_audio and allow_tts and tts_text:
                self.pipeline.tts.synthesize_to_file(tts_text, out_path)
                audio_output_path = out_path

            return {
                "asr_text": None,
                "assistant_text": frontend_text,
                "assistant_payload": parsed_payload,
                "audio_output_path": audio_output_path,
            }

    def voice_chat(
        self,
        user_key: str,
        username: str,
        input_audio_path: str,
        output_audio_path: str | None,
        prompt_id: int | None = None,
        prompt: str | None = None,
        with_audio: bool = True,
    ) -> dict:
        session_lock = self._get_session_lock(user_key)
        with session_lock:
            history = self._history(user_key)
            self._compress_history_if_needed(history)
            result = self.pipeline.run_from_audio(
                audio_path=input_audio_path,
                history=history,
                output_audio_path=None,
                language="zh_cn",
                stream_to_console=False,
                system_prompt=prompt,
                enable_tts=False,
            )

            parsed_payload = self._try_parse_json(result.assistant_text)
            tts_text, allow_tts = self._decide_tts_text(prompt_id, result.assistant_text, parsed_payload)
            frontend_text = self._decide_frontend_text(prompt_id, result.assistant_text, parsed_payload)

            audio_final_path = None
            if with_audio and allow_tts and tts_text and output_audio_path:
                self.pipeline.tts.synthesize_to_file(tts_text, output_audio_path)
                audio_final_path = output_audio_path

            return {
                "asr_text": result.user_text,
                "assistant_text": frontend_text,
                "assistant_payload": parsed_payload,
                "audio_output_path": audio_final_path,
            }

    @staticmethod
    def _try_parse_json(text: str) -> dict[str, Any] | None:
        def _loads(candidate: str) -> dict[str, Any] | None:
            try:
                obj = json.loads(candidate)
                return obj if isinstance(obj, dict) else None
            except Exception:
                return None

        # 1) 直接解析
        direct = _loads(text)
        if direct is not None:
            return direct

        cleaned = text.strip()

        # 2) 处理 ```json ... ``` 包裹
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            fenced = "\n".join(lines).strip()
            fenced_obj = _loads(fenced)
            if fenced_obj is not None:
                return fenced_obj

        # 3) 截取首尾大括号的JSON片段再解析
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = cleaned[start : end + 1]
            snippet_obj = _loads(snippet)
            if snippet_obj is not None:
                return snippet_obj

        return None

    @staticmethod
    def _looks_like_json_blob(text: str) -> bool:
        t = (text or "").strip()
        if not t:
            return False
        if (t.startswith("{") and t.endswith("}")) or (t.startswith("[") and t.endswith("]")):
            return True
        if "```json" in t or "\"intent\"" in t or "\"schedule_action\"" in t:
            return True
        return False

    @staticmethod
    def _decide_tts_text(
        prompt_id: int | None,
        assistant_text: str,
        parsed_payload: dict[str, Any] | None,
    ) -> tuple[str | None, bool]:
        # prompt 1：
        # - normal_chat: 仅播报 reply_text
        # - schedule_edit: 不做TTS，直接返回JSON
        if prompt_id == 1 and parsed_payload:
            intent = str(parsed_payload.get("intent", "")).strip()
            if intent == "schedule_edit":
                return None, False
            reply_text = str(parsed_payload.get("reply_text", "")).strip()
            return (reply_text if reply_text else None), bool(reply_text)

        # prompt 1 且解析失败时：
        # - 若文本看起来仍是结构化JSON片段，继续禁播报，避免读出模板内容
        # - 否则降级为自然语言播报，避免前端拿不到音频
        if prompt_id == 1 and not parsed_payload:
            if VoiceAgentService._looks_like_json_blob(assistant_text):
                return None, False
            fallback_text = assistant_text.strip()
            return (fallback_text if fallback_text else None), bool(fallback_text)

        # 其他场景：优先播报 reply_text（若存在），否则播报原始文本
        if parsed_payload and isinstance(parsed_payload.get("reply_text"), str):
            reply_text = str(parsed_payload.get("reply_text", "")).strip()
            if reply_text:
                return reply_text, True
        return assistant_text, True

    @staticmethod
    def _decide_frontend_text(
        prompt_id: int | None,
        assistant_text: str,
        parsed_payload: dict[str, Any] | None,
    ) -> str:
        # prompt 1 normal_chat：前端仅接收 reply_text，避免返回整段JSON模板文本
        if prompt_id == 1 and parsed_payload:
            intent = str(parsed_payload.get("intent", "")).strip()
            if intent == "normal_chat":
                reply_text = str(parsed_payload.get("reply_text", "")).strip()
                if reply_text:
                    return reply_text
            # schedule_edit 保持JSON文本回传给前端处理
            if intent == "schedule_edit":
                return json.dumps(parsed_payload, ensure_ascii=False)

        # 通用兜底：若有 reply_text 则优先返回
        if parsed_payload and isinstance(parsed_payload.get("reply_text"), str):
            reply_text = str(parsed_payload.get("reply_text", "")).strip()
            if reply_text:
                return reply_text
        return assistant_text


def build_auth_response(user):
    token = create_access_token(user.username)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "created_at": user.created_at,
        },
    }
