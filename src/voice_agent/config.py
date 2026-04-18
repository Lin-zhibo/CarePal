import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


# 语音链路配置：ASR/LLM/TTS/RAG 都从这里读取。
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
    context_max_turns: int = int(os.getenv("CONTEXT_MAX_TURNS", "50"))
    memory_path: str = os.getenv("MEMORY_PATH", "memory/history.json")
    rag_enabled: bool = os.getenv("RAG_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    rag_db_path: str = os.getenv("RAG_DB_PATH", "db/chroma")
    rag_state_db_path: str = os.getenv("RAG_STATE_DB_PATH", "db/rag_sync_state.db")
    rag_data_dir: str = os.getenv("RAG_DATA_DIR", "data")
    rag_chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "500"))
    rag_chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "80"))
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "")
    embedding_model_url: str = os.getenv("EMBEDDING_MODEL_URL", "")
    embedding_model_api: str = os.getenv("EMBEDDING_MODEL_API", "")
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "3"))
    rag_max_context_chars: int = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "1200"))


def get_settings() -> Settings:
    return Settings()
