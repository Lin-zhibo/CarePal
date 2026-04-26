from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from src.voice_agent.config import get_settings
from src.voice_agent.rag import SimpleRAGStore, SyncReport


logger = logging.getLogger(__name__)


def _r03(raw_path: str) -> str:
    """
    Resolve a possibly-relative path against project root.

    Args:
        raw_path (str): Input path from settings, can be relative or absolute.

    Returns:
        str: Absolute normalized path string.

    This function keeps runtime behavior stable across different launch directories.
    """

    p01 = Path(raw_path)
    if p01.is_absolute():
        return str(p01)

    rt01 = Path(__file__).resolve().parents[2]
    return str((rt01 / p01).resolve())


def sync_rag_knowledge_on_startup() -> SyncReport | None:
    # 后端启动时调用：把 data 目录内容同步到向量库。
    """
    Perform incremental RAG synchronization during backend startup.

    Args:
        None: This function reads all required settings from environment-backed config.

    Returns:
        SyncReport | None: Detailed sync result, or None when sync fails.

    The function checks file add/remove/content changes under data directory and re-indexes only affected files.
    """

    s01 = get_settings()

    d01 = _r03(s01.rag_data_dir)
    c01 = _r03(s01.rag_db_path)
    st01 = _r03(s01.rag_state_db_path)

    st02 = SimpleRAGStore(
        db_path=c01,
        state_db_path=st01,
        embedding_model=s01.embedding_model,
        embedding_base_url=s01.embedding_model_url,
        embedding_api_key=s01.embedding_model_api,
        chunk_size=s01.rag_chunk_size,
        chunk_overlap=s01.rag_chunk_overlap,
    )

    try:
        rp01 = st02.sync_data_directory(data_dir=d01)
    except (RuntimeError, ValueError, OSError, sqlite3.Error):
        logger.exception("RAG startup sync failed")
        return None

    logger.info(
        "RAG startup sync complete: added=%d updated=%d removed=%d skipped=%d indexed_chunks=%d",
        len(rp01.added_files),
        len(rp01.updated_files),
        len(rp01.removed_files),
        len(rp01.skipped_files),
        rp01.indexed_chunks,
    )
    return rp01

