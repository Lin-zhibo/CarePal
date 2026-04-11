from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import Any
from typing import Dict, List

from sqlalchemy.orm import Session

from src.voice_agent.config import get_settings
from src.voice_agent.pipeline import VoicePipeline

from .models import User
from .security import create_access_token, hash_password, verify_password


class UserService:
    @staticmethod
    def register(db: Session, username: str, password: str):
        exists = db.query(User).filter(User.username == username).first()
        if exists:
            return None
        user = User(username=username, password_hash=hash_password(password))
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


class VoiceAgentService:
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

        # prompt 1 且解析失败时，为避免把结构化模板原文做TTS，默认不播报
        if prompt_id == 1 and not parsed_payload:
            return None, False

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
