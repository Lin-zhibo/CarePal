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
        q01 = db.query(User).filter(User.username == username).first()
        if q01:
            return None
        u01 = User(
            username=username,
            password_hash=hash_password(password),
            emergency_contact_name=emergency_contact_name,
            emergency_contact_email=emergency_contact_email,
        )
        db.add(u01)
        db.commit()
        db.refresh(u01)
        return u01

    @staticmethod
    def login(db: Session, username: str, password: str):
        u01 = db.query(User).filter(User.username == username).first()
        if not u01:
            return None
        if not verify_password(password, u01.password_hash):
            return None
        return u01

    @staticmethod
    def get_emergency_contact(db: Session, username: str) -> dict[str, str | None] | None:
        u01 = db.query(User).filter(User.username == username).first()
        if u01 is None:
            return None
        return {
            "emergency_contact_name": u01.emergency_contact_name,
            "emergency_contact_email": u01.emergency_contact_email,
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
            target=self._e19,
            args=(resolve_alert_target_by_token,),
            daemon=True,
            name="emergency-alert-listener",
        )
        thread.start()
        logger.info("Emergency alert listener started at %s:%s", self.host, self.port)
        return thread

    @staticmethod
    def _e13(value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            v01 = value.strip().lower()
            if v01 in {"1", "true", "yes", "on"}:
                return True
            if v01 in {"0", "false", "no", "off"}:
                return False
        return default

    def _e17(self, payload: str) -> dict[str, Any] | None:
        # 兼容两种输入：JSON 报文 / 直接传 token 字符串。
        p01 = payload.strip()
        if not p01:
            return None

        d01: dict[str, Any]
        try:
            j01 = json.loads(p01)
            d01 = j01 if isinstance(j01, dict) else {}
        except json.JSONDecodeError:
            d01 = {"token": p01}

        t01 = str(d01.get("token", "")).strip()
        if not t01:
            return None

        m01 = str(d01.get("type", "")).strip()
        if m01 and m01 != "emergency_fall_alert":
            return None

        return d01

    def _e19(self, resolve_alert_target_by_token) -> None:
        # 常驻循环：单连接读取单条报文，处理完成后关闭连接。
        s01 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s01.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s01.bind((self.host, self.port))
        s01.listen(5)

        while True:
            c01, a01 = s01.accept()
            with c01:
                try:
                    b01 = c01.recv(4096)
                    if not b01:
                        continue
                    r01 = b01.decode("utf-8", errors="ignore")
                    p01 = self._e17(r01)
                    if not p01:
                        logger.warning("Emergency alert payload is invalid or trigger mismatch from %s", a01)
                        continue

                    t01 = str(p01.get("token", "")).strip()
                    a02 = resolve_alert_target_by_token(t01)
                    if not a02:
                        logger.warning("Emergency alert ignored because token has no matching user. from=%s", a01)
                        continue

                    self.send_alert_email(a02, p01)
                except Exception as e01:
                    logger.exception("Emergency alert listener failed to handle request from %s: %s", a01, e01)

    def send_alert_email(self, alert_target: dict[str, str | None], payload_overrides: dict[str, Any] | None = None) -> None:
        r01 = (alert_target.get("emergency_contact_email") or "").strip()
        n01 = (alert_target.get("emergency_contact_name") or "").strip() or "紧急联系人"
        u01 = (alert_target.get("username") or "").strip() or "该用户"

        if not r01:
            logger.warning("Emergency alert skipped because recipient email is empty. user=%s", u01)
            return

        raw01 = payload_overrides or {}
        nest01 = raw01.get("smtp_override") if isinstance(raw01, dict) else None
        if isinstance(nest01, dict):
            ov01 = {**raw01, **nest01}
        else:
            ov01 = raw01

        h01 = str(ov01.get("smtp_host", self.smtp_host) or "").strip()
        p01 = int(ov01.get("smtp_port", self.smtp_port) or self.smtp_port)
        un01 = str(ov01.get("smtp_username", self.smtp_username) or "").strip()
        pw01 = str(ov01.get("smtp_password", self.smtp_password) or "").strip()
        se01 = str(ov01.get("smtp_sender_email", self.smtp_sender_email) or "").strip()
        tls01 = self._e13(ov01.get("smtp_use_tls"), self.smtp_use_tls)
        ssl01 = self._e13(ov01.get("smtp_use_ssl"), self.smtp_use_ssl)

        if not h01 or not se01:
            logger.warning("Emergency alert skipped because smtp_host or smtp_sender_email is empty")
            return

        m01 = EmailMessage()
        m01["From"] = se01
        m01["To"] = r01
        m01["Subject"] = self.email_subject or "CarePal 紧急提醒"
        t01 = self.email_body or "（{contact_name}）你好，你家里的老人（{username}）可能刚才跌倒了，请尽快打电话确认老人情况！！！"
        try:
            b01 = t01.format(contact_name=n01, username=u01)
        except Exception:
            b01 = t01
        m01.set_content(b01)

        if ssl01:
            c01 = smtplib.SMTP_SSL
        else:
            c01 = smtplib.SMTP

        with c01(h01, p01, timeout=20) as s01:
            if (not ssl01) and tls01:
                s01.starttls()
            if un01 and pw01:
                s01.login(un01, pw01)
            s01.send_message(m01)
        logger.info("Emergency alert email sent successfully. user=%s recipient=%s", u01, r01)


class VoiceAgentService:
    # 对 VoicePipeline 做会话级封装，管理历史和并发锁。
    def __init__(self) -> None:
        self.settings = get_settings()
        self.pipeline = VoicePipeline(self.settings)
        self.user_histories: Dict[str, List[Dict[str, str]]] = {}
        self._session_locks: Dict[str, threading.Lock] = {}
        self._manager_lock = threading.RLock()

    def _v11(self, user_key: str) -> List[Dict[str, str]]:
        with self._manager_lock:
            if user_key not in self.user_histories:
                self.user_histories[user_key] = []
            return self.user_histories[user_key]

    def _v13(self, user_key: str) -> threading.Lock:
        with self._manager_lock:
            if user_key not in self._session_locks:
                self._session_locks[user_key] = threading.Lock()
            return self._session_locks[user_key]

    @staticmethod
    def _v17(history: List[Dict[str, str]]) -> None:
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
        session_lock = self._v13(user_key)
        with session_lock:
            history = self._v11(user_key)
            self._v17(history)
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
            parsed_payload = self._v23(result.assistant_text)
            tts_text, allow_tts = self._v29(prompt_id, result.assistant_text, parsed_payload)
            frontend_text = self._v31(prompt_id, result.assistant_text, parsed_payload)

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
        session_lock = self._v13(user_key)
        with session_lock:
            history = self._v11(user_key)
            self._v17(history)
            result = self.pipeline.run_from_audio(
                audio_path=input_audio_path,
                history=history,
                output_audio_path=None,
                language="zh_cn",
                stream_to_console=False,
                system_prompt=prompt,
                enable_tts=False,
            )

            parsed_payload = self._v23(result.assistant_text)
            tts_text, allow_tts = self._v29(prompt_id, result.assistant_text, parsed_payload)
            frontend_text = self._v31(prompt_id, result.assistant_text, parsed_payload)

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
    def _v23(text: str) -> dict[str, Any] | None:
        def _v25(candidate: str) -> dict[str, Any] | None:
            try:
                o01 = json.loads(candidate)
                return o01 if isinstance(o01, dict) else None
            except Exception:
                return None

        # 1) 直接解析
        direct = _v25(text)
        if direct is not None:
            return direct

        c01 = text.strip()

        # 2) 处理 ```json ... ``` 包裹
        if c01.startswith("```"):
            l01 = c01.splitlines()
            if l01 and l01[0].startswith("```"):
                l01 = l01[1:]
            if l01 and l01[-1].strip() == "```":
                l01 = l01[:-1]
            f01 = "\n".join(l01).strip()
            o01 = _v25(f01)
            if o01 is not None:
                return o01

        # 3) 截取首尾大括号的JSON片段再解析
        s01 = c01.find("{")
        e01 = c01.rfind("}")
        if s01 != -1 and e01 != -1 and e01 > s01:
            sn01 = c01[s01 : e01 + 1]
            o01 = _v25(sn01)
            if o01 is not None:
                return o01

        return None

    @staticmethod
    def _v27(text: str) -> bool:
        t01 = (text or "").strip()
        if not t01:
            return False
        if (t01.startswith("{") and t01.endswith("}")) or (t01.startswith("[") and t01.endswith("]")):
            return True
        if "```json" in t01 or "\"intent\"" in t01 or "\"schedule_action\"" in t01:
            return True
        return False

    @staticmethod
    def _v29(
        prompt_id: int | None,
        assistant_text: str,
        parsed_payload: dict[str, Any] | None,
    ) -> tuple[str | None, bool]:
        # prompt 1：
        # - normal_chat: 仅播报 reply_text
        # - schedule_edit: 不做TTS，直接返回JSON
        if prompt_id == 1 and parsed_payload:
            i01 = str(parsed_payload.get("intent", "")).strip()
            if i01 == "schedule_edit":
                return None, False
            r01 = str(parsed_payload.get("reply_text", "")).strip()
            return (r01 if r01 else None), bool(r01)

        # prompt 1 且解析失败时：
        # - 若文本看起来仍是结构化JSON片段，继续禁播报，避免读出模板内容
        # - 否则降级为自然语言播报，避免前端拿不到音频
        if prompt_id == 1 and not parsed_payload:
            if VoiceAgentService._v27(assistant_text):
                return None, False
            f01 = assistant_text.strip()
            return (f01 if f01 else None), bool(f01)

        # 其他场景：优先播报 reply_text（若存在），否则播报原始文本
        if parsed_payload and isinstance(parsed_payload.get("reply_text"), str):
            r01 = str(parsed_payload.get("reply_text", "")).strip()
            if r01:
                return r01, True
        return assistant_text, True

    @staticmethod
    def _v31(
        prompt_id: int | None,
        assistant_text: str,
        parsed_payload: dict[str, Any] | None,
    ) -> str:
        # prompt 1 normal_chat：前端仅接收 reply_text，避免返回整段JSON模板文本
        if prompt_id == 1 and parsed_payload:
            i01 = str(parsed_payload.get("intent", "")).strip()
            if i01 == "normal_chat":
                r01 = str(parsed_payload.get("reply_text", "")).strip()
                if r01:
                    return r01
            # schedule_edit 保持JSON文本回传给前端处理
            if i01 == "schedule_edit":
                return json.dumps(parsed_payload, ensure_ascii=False)

        # 通用兜底：若有 reply_text 则优先返回
        if parsed_payload and isinstance(parsed_payload.get("reply_text"), str):
            r01 = str(parsed_payload.get("reply_text", "")).strip()
            if r01:
                return r01
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
