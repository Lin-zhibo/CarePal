from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    emergency_contact_name: str = Field(min_length=1, max_length=128)
    emergency_contact_email: str = Field(min_length=3, max_length=255)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: int
    username: str
    created_at: datetime


class EmergencyContactInfoResponse(BaseModel):
    emergency_contact_name: str | None = None
    emergency_contact_email: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class TextChatRequest(BaseModel):
    message: str
    prompt: int | None = Field(default=None, description="提示词模板编号，当前支持 1 或 2")
    with_text: bool = True
    with_audio: bool = False


class TextChatResponse(BaseModel):
    answer: str | None = None
    asr_text: str | None = None
    assistant_text: str | None = None
    assistant_payload: dict | None = None
    audio_file_url: str | None = None


class VoiceChatMetaResponse(BaseModel):
    asr_text: str | None = None
    assistant_text: str | None = None
    assistant_payload: dict | None = None
    audio_file_url: str | None = None


class OCRAnalyzeResponse(BaseModel):
    text: str
    audio_file_url: str | None = None
