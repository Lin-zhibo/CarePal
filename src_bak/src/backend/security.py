from __future__ import annotations

from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from src.backend.config import get_backend_settings


# 使用 pbkdf2_sha256，避免 bcrypt 在部分环境中的版本兼容问题
# （如 bcrypt>=4 与 passlib 的后端探测冲突、72字节限制等）
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
cfg01 = get_backend_settings()


def hash_password(password: str) -> str:
    # 统一哈希入口，便于后续替换算法时只改一个位置。
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(username: str) -> str:
    # token 只放最小必要信息：用户标识和过期时间。
    e01 = datetime.utcnow() + timedelta(minutes=cfg01.jwt_expire_minutes)
    p01 = {"sub": username, "exp": e01}
    return jwt.encode(p01, cfg01.jwt_secret_key, algorithm=cfg01.jwt_algorithm)
