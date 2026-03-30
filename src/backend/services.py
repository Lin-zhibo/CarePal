from __future__ import annotations

import os
from datetime import datetime
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

    def _history(self, username: str) -> List[Dict[str, str]]:
        if username not in self.user_histories:
            self.user_histories[username] = []
        return self.user_histories[username]

    def text_chat(self, username: str, message: str) -> str:
        history = self._history(username)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        out_path = os.path.join("outputs", "backend", f"{username}_{ts}.mp3")
        result = self.pipeline.run_from_text(
            user_text=message,
            history=history,
            output_audio_path=out_path,
            stream_to_console=False,
        )
        return result.assistant_text

    def voice_chat(self, username: str, input_audio_path: str, output_audio_path: str) -> dict:
        history = self._history(username)
        result = self.pipeline.run_from_audio(
            audio_path=input_audio_path,
            history=history,
            output_audio_path=output_audio_path,
            language="zh_cn",
            stream_to_console=False,
        )
        return {
            "asr_text": result.user_text,
            "assistant_text": result.assistant_text,
            "audio_output_path": result.audio_output_path,
        }


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
