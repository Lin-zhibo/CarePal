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
    alert_listener_host: str = os.getenv("ALERT_LISTENER_HOST", "127.0.0.1")
    alert_listener_port: int = int(os.getenv("ALERT_LISTENER_PORT", "0"))
    alert_trigger_keyword: str = os.getenv("ALERT_TRIGGER_KEYWORD", "")
    alert_email_subject: str = os.getenv("ALERT_EMAIL_SUBJECT", "")
    alert_email_body: str = os.getenv("ALERT_EMAIL_BODY", "")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_sender_email: str = os.getenv("SMTP_SENDER_EMAIL", "")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}
    smtp_use_ssl: bool = os.getenv("SMTP_USE_SSL", "false").strip().lower() in {"1", "true", "yes", "on"}


def get_backend_settings() -> BackendSettings:
    return BackendSettings()
