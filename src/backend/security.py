from __future__ import annotations

from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from src.backend.config import get_backend_settings


# 使用 pbkdf2_sha256，避免 bcrypt 在部分环境中的版本兼容问题
# （如 bcrypt>=4 与 passlib 的后端探测冲突、72字节限制等）
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
settings = get_backend_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
