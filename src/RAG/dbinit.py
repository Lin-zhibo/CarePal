from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from src.voice_agent.config import get_settings
from src.voice_agent.rag import SimpleRAGStore, SyncReport


logger = logging.getLogger(__name__)


def _resolve_project_path(raw_path: str) -> str:
    """
    Resolve a possibly-relative path against project root.

    Args:
        raw_path (str): Input path from settings, can be relative or absolute.

    Returns:
        str: Absolute normalized path string.

    This function keeps runtime behavior stable across different launch directories.
    """

    path = Path(raw_path)
    if path.is_absolute():
        return str(path)

    project_root = Path(__file__).resolve().parents[2]
    return str((project_root / path).resolve())


def sync_rag_knowledge_on_startup() -> SyncReport | None:
    """
    Perform incremental RAG synchronization during backend startup.

    Args:
        None: This function reads all required settings from environment-backed config.

    Returns:
        SyncReport | None: Detailed sync result, or None when sync fails.

    The function checks file add/remove/content changes under data directory and re-indexes only affected files.
    """

    settings = get_settings()

    data_dir = _resolve_project_path(settings.rag_data_dir)
    chroma_dir = _resolve_project_path(settings.rag_db_path)
    state_db_path = _resolve_project_path(settings.rag_state_db_path)

    store = SimpleRAGStore(
        db_path=chroma_dir,
        state_db_path=state_db_path,
        embedding_model=settings.embedding_model,
        embedding_base_url=settings.embedding_model_url,
        embedding_api_key=settings.embedding_model_api,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )

    try:
        report = store.sync_data_directory(data_dir=data_dir)
    except (RuntimeError, ValueError, OSError, sqlite3.Error):
        logger.exception("RAG startup sync failed")
        return None

    logger.info(
        "RAG startup sync complete: added=%d updated=%d removed=%d skipped=%d indexed_chunks=%d",
        len(report.added_files),
        len(report.updated_files),
        len(report.removed_files),
        len(report.skipped_files),
        report.indexed_chunks,
    )
    return report

