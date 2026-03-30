from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "doc" / ".env")


@dataclass
class BackendSettings:
    app_name: str = os.getenv("APP_NAME", "voice-agent-backend")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    debug: bool = os.getenv("DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///memory/backend.db")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-this-in-prod")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))


def get_backend_settings() -> BackendSettings:
    return BackendSettings()
