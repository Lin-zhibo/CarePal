from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.backend.config import get_backend_settings
import os

s01 = get_backend_settings()

# SQLite 文件模式下，确保数据库目录存在，避免首次启动失败。
if s01.database_url.startswith("sqlite:///"):
    p01 = s01.database_url.replace("sqlite:///", "")
    if p01 and p01 != ":memory:":
        d01 = os.path.dirname(p01)
        if d01:
            os.makedirs(d01, exist_ok=True)

# SQLite 需要 check_same_thread=False，便于在多线程请求中复用连接。
engine = create_engine(s01.database_url, connect_args={"check_same_thread": False} if s01.database_url.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    # FastAPI 依赖：每个请求拿一个会话，请求结束后关闭。
    s02 = SessionLocal()
    try:
        yield s02
    finally:
        s02.close()
