import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "doc" / ".env")


@dataclass
class Settings:
    xfyun_app_id: str = os.getenv("XFYUN_APP_ID", "")
    xfyun_api_key: str = os.getenv("XFYUN_API_KEY", "")
    xfyun_api_secret: str = os.getenv("XFYUN_API_SECRET", "")
    xfyun_llm_api_password: str = os.getenv("XFYUN_LLM_API_PASSWORD", "")
    xfyun_tts_host: str = os.getenv("XFYUN_TTS_HOST", "api-dx.xf-yun.com")
    asr_model: str = os.getenv("ASR_MODEL", "slm")
    llm_model: str = os.getenv("LLM_MODEL", "4.0Ultra")
    tts_voice: str = os.getenv("TTS_VOICE", "x4_yeting")
    tts_poll_interval_seconds: float = float(os.getenv("TTS_POLL_INTERVAL_SECONDS", "1.0"))
    tts_max_wait_seconds: int = int(os.getenv("TTS_MAX_WAIT_SECONDS", "180"))
    tts_max_chars_per_task: int = int(os.getenv("TTS_MAX_CHARS_PER_TASK", "220"))
    memory_path: str = os.getenv("MEMORY_PATH", "memory/history.json")
    rag_enabled: bool = os.getenv("RAG_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    rag_db_path: str = os.getenv("RAG_DB_PATH", "memory/rag_knowledge.db")
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "3"))
    rag_max_context_chars: int = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "1200"))


def get_settings() -> Settings:
    return Settings()
