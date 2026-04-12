from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import SecretStr


logger = logging.getLogger(__name__)


@dataclass
class RetrievalItem:
    """
    Represent a single retrieval hit from the vector store.

    Args:
        id (int): Runtime-generated identifier for ordering and diagnostics.
        source (str): Source file path or logical source name of this chunk.
        content (str): Retrieved text content.
        score (int): Relevance score where larger means more relevant.

    Returns:
        RetrievalItem: Dataclass instance that stores retrieval payload.

    This DTO is used by the RAG pipeline to keep retrieval outputs structured.
    """

    id: int
    source: str
    content: str
    score: int


@dataclass
class SyncReport:
    """
    Summarize the incremental indexing result for a startup sync run.

    Args:
        added_files (list[str]): Files newly discovered and indexed.
        updated_files (list[str]): Files whose content changed and were re-indexed.
        removed_files (list[str]): Files removed from disk and from index state.
        skipped_files (list[str]): Files skipped because parsing or indexing failed.
        indexed_chunks (int): Total number of chunks indexed in this run.

    Returns:
        SyncReport: Dataclass instance carrying synchronization statistics.

    This report is mainly used for logging and startup health observation.
    """

    added_files: List[str]
    updated_files: List[str]
    removed_files: List[str]
    skipped_files: List[str]
    indexed_chunks: int


@dataclass
class _FileState:
    """
    Store persisted state metadata for one indexed source file.

    Args:
        file_path (str): Relative file path under the monitored data directory.
        content_hash (str): MD5 hash of the file content for change detection.
        dataset_dir (str): Chroma persistence directory for this file.

    Returns:
        _FileState: Internal dataclass representing one state table row.

    The class is internal and used to compare previous and current file states.
    """

    file_path: str
    content_hash: str
    dataset_dir: str


class SimpleRAGStore:
    """
    Provide a lightweight RAG store powered by LangChain + Chroma.

    Args:
        db_path (str): Directory path used by Chroma to persist vector datasets.
        state_db_path (str | None): Optional SQLite state DB path for file change tracking.
        embedding_model (str | None): Embedding model name. If None, read from env.
        embedding_base_url (str | None): Embedding API base URL. If None, read from env.
        embedding_api_key (str | None): Embedding API key. If None, read from env.
        chunk_size (int): Split chunk size, recommended range is 100-4000.
        chunk_overlap (int): Overlap size between adjacent chunks, range [0, chunk_size-1].

    Returns:
        None: Initializes directories, state database schema, and lazy embedding config.

    The class supports both retrieval and startup incremental indexing by file granularity.
    """

    def __init__(
        self,
        db_path: str,
        state_db_path: str | None = None,
        embedding_model: str | None = None,
        embedding_base_url: str | None = None,
        embedding_api_key: str | None = None,
        chunk_size: int = 500,
        chunk_overlap: int = 80,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.state_db_path = Path(state_db_path) if state_db_path else self.db_path.parent / "rag_sync_state.db"
        self.state_db_path.parent.mkdir(parents=True, exist_ok=True)

        self.embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "")
        self.embedding_base_url = embedding_base_url or os.getenv("EMBEDDING_MODEL_URL", "")
        self.embedding_api_key = embedding_api_key or os.getenv("EMBEDDING_MODEL_API", "")

        self.chunk_size = max(100, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size - 1))
        self.collection_name = "knowledge"
        self._embeddings: OpenAIEmbeddings | None = None

        self._init_state_schema()

    def _init_state_schema(self) -> None:
        """
        Create SQLite schema used for file change tracking.

        Args:
            None: This method has no external input parameters.

        Returns:
            None: Ensures required table exists.

        The table keeps one row per source file to support incremental indexing.
        """

        with sqlite3.connect(str(self.state_db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_file_state (
                    file_path TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    dataset_dir TEXT NOT NULL,
                    indexed_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @staticmethod
    def _now_iso() -> str:
        """
        Produce an ISO timestamp in UTC timezone.

        Args:
            None: This method has no external input parameters.

        Returns:
            str: ISO formatted UTC timestamp.

        The timestamp is used by the state table to track index update time.
        """

        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalize whitespace in text content.

        Args:
            text (str): Input text string, can contain arbitrary whitespace.

        Returns:
            str: Text with consecutive whitespaces collapsed to a single space.

        The normalization improves consistency for retrieval display and scoring.
        """

        return re.sub(r"\s+", " ", text.strip())

    @staticmethod
    def _compute_content_hash(file_path: Path) -> str:
        """
        Compute MD5 hash for a file to detect content changes.

        Args:
            file_path (Path): Existing file path to hash.

        Returns:
            str: Hex digest string of the file content.

        This hash is used for startup incremental sync decisions.
        """

        digest = hashlib.md5()
        with file_path.open("rb") as fp:
            while True:
                chunk = fp.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _sanitize_name(raw: str) -> str:
        """
        Convert a raw string into a filesystem-safe dataset name fragment.

        Args:
            raw (str): Raw input string, usually file stem.

        Returns:
            str: Sanitized name containing only letters, digits, underscore, and dash.

        This is used to create deterministic and safe dataset directories.
        """

        safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw).strip("_")
        return safe or "dataset"

    def _dataset_dir_for_file(self, relative_file_path: str) -> Path:
        """
        Build deterministic Chroma persistence directory for one source file.

        Args:
            relative_file_path (str): Path relative to monitored data directory.

        Returns:
            Path: Chroma directory path for this file.

        One file maps to one Chroma dataset directory to satisfy per-file isolation.
        """

        stem = self._sanitize_name(Path(relative_file_path).stem)
        digest = hashlib.sha1(relative_file_path.encode("utf-8")).hexdigest()[:12]
        return self.db_path / f"{stem}_{digest}"

    @staticmethod
    def _scan_json_files(data_dir: str) -> dict[str, Path]:
        """
        Discover JSON files under a data directory recursively.

        Args:
            data_dir (str): Root directory to scan.

        Returns:
            dict[str, Path]: Mapping from relative POSIX path to absolute file path.

        The scanner currently limits indexing input to JSON files only.
        """

        root = Path(data_dir)
        if not root.exists() or not root.is_dir():
            return {}

        discovered: dict[str, Path] = {}
        for file_path in sorted(root.rglob("*.json")):
            if file_path.is_file():
                rel = file_path.relative_to(root).as_posix()
                discovered[rel] = file_path
        return discovered

    def _load_state_map(self) -> dict[str, _FileState]:
        """
        Read all persisted file states from SQLite.

        Args:
            None: This method has no external input parameters.

        Returns:
            dict[str, _FileState]: Keyed by relative file path.

        This method provides baseline state for incremental sync comparison.
        """

        with sqlite3.connect(str(self.state_db_path)) as conn:
            rows = conn.execute(
                "SELECT file_path, content_hash, dataset_dir FROM rag_file_state"
            ).fetchall()

        return {
            row[0]: _FileState(file_path=row[0], content_hash=row[1], dataset_dir=row[2])
            for row in rows
        }

    def _upsert_state_entry(self, file_path: str, content_hash: str, dataset_dir: str) -> None:
        """
        Insert or update one file state row.

        Args:
            file_path (str): Relative file path in monitored data directory.
            content_hash (str): Latest content hash value.
            dataset_dir (str): Chroma dataset directory path.

        Returns:
            None: Persists state update into SQLite.

        Upsert keeps state stable across restarts while supporting file mutations.
        """

        with sqlite3.connect(str(self.state_db_path)) as conn:
            conn.execute(
                """
                INSERT INTO rag_file_state (file_path, content_hash, dataset_dir, indexed_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(file_path)
                DO UPDATE SET
                    content_hash = excluded.content_hash,
                    dataset_dir = excluded.dataset_dir,
                    indexed_at = excluded.indexed_at
                """,
                (file_path, content_hash, dataset_dir, self._now_iso()),
            )
            conn.commit()

    def _delete_state_entry(self, file_path: str) -> None:
        """
        Delete one file state row after source removal.

        Args:
            file_path (str): Relative file path to remove from state DB.

        Returns:
            None: Removes state row if present.

        This keeps tracking table aligned with current data directory.
        """

        with sqlite3.connect(str(self.state_db_path)) as conn:
            conn.execute("DELETE FROM rag_file_state WHERE file_path = ?", (file_path,))
            conn.commit()

    def _get_embeddings(self) -> OpenAIEmbeddings:
        """
        Lazily build and cache embedding client from configuration.

        Args:
            None: This method has no external input parameters.

        Returns:
            OpenAIEmbeddings: Ready-to-use embedding client.

        The method validates required embedding config before creating the client.
        """

        if self._embeddings is not None:
            return self._embeddings

        if not self.embedding_model or not self.embedding_base_url or not self.embedding_api_key:
            raise RuntimeError(
                "Embedding configuration is incomplete. "
                "Please set EMBEDDING_MODEL, EMBEDDING_MODEL_URL, and EMBEDDING_MODEL_API."
            )

        self._embeddings = OpenAIEmbeddings(
            model=self.embedding_model,
            api_key=SecretStr(self.embedding_api_key),
            base_url=self.embedding_base_url,
        )
        return self._embeddings

    def _parse_json_documents(self, file_path: Path, relative_file_path: str) -> List[Document]:
        """
        Parse a JSON file into LangChain documents.

        Args:
            file_path (Path): Absolute path of a JSON file.
            relative_file_path (str): Relative path used as source metadata.

        Returns:
            list[Document]: Parsed documents ready for splitting and indexing.

        The parser is optimized for QA JSON while providing generic JSON fallback.
        """

        raw_text = file_path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)
        documents: List[Document] = []

        if isinstance(payload, list):
            for idx, item in enumerate(payload):
                if isinstance(item, dict):
                    canonical_question = str(item.get("canonical_question", "")).strip()
                    answer = str(item.get("answer", "")).strip()
                    question_variants = item.get("question_variants")

                    questions: List[str] = []
                    if canonical_question:
                        questions.append(canonical_question)
                    if isinstance(question_variants, list):
                        for variant in question_variants:
                            variant_text = str(variant).strip()
                            if variant_text:
                                questions.append(variant_text)

                    merged_questions = list(dict.fromkeys(questions))
                    if not merged_questions and not answer:
                        continue

                    content_lines: List[str] = []
                    if merged_questions:
                        content_lines.append(f"Question: {' / '.join(merged_questions)}")
                    if answer:
                        content_lines.append(f"Answer: {answer}")

                    documents.append(
                        Document(
                            page_content="\n".join(content_lines),
                            metadata={
                                "source": relative_file_path,
                                "record_index": idx,
                            },
                        )
                    )
                else:
                    documents.append(
                        Document(
                            page_content=json.dumps(item, ensure_ascii=False),
                            metadata={
                                "source": relative_file_path,
                                "record_index": idx,
                            },
                        )
                    )
            return documents

        if isinstance(payload, dict):
            return [
                Document(
                    page_content=json.dumps(payload, ensure_ascii=False),
                    metadata={"source": relative_file_path, "record_index": 0},
                )
            ]

        return [
            Document(
                page_content=str(payload),
                metadata={"source": relative_file_path, "record_index": 0},
            )
        ]

    def _split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split raw documents into overlapping chunks for indexing.

        Args:
            documents (list[Document]): Input document list before chunking.

        Returns:
            list[Document]: Chunked documents suitable for vector indexing.

        Chunking improves retrieval granularity and context relevance.
        """

        if not documents:
            return []

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ";", "；", ",", "，", " ", ""],
        )
        return splitter.split_documents(documents)

    def _rebuild_file_index(self, file_path: Path, relative_file_path: str) -> tuple[str, int]:
        """
        Rebuild the Chroma dataset for a single source file.

        Args:
            file_path (Path): Absolute path to source JSON file.
            relative_file_path (str): Relative source path used as identity key.

        Returns:
            tuple[str, int]: Dataset directory path and indexed chunk count.

        The method enforces full rebuild per changed file for deterministic consistency.
        """

        raw_documents = self._parse_json_documents(file_path=file_path, relative_file_path=relative_file_path)
        chunked_documents = self._split_documents(raw_documents)

        dataset_dir = self._dataset_dir_for_file(relative_file_path)
        if dataset_dir.exists():
            shutil.rmtree(dataset_dir, ignore_errors=True)

        if not chunked_documents:
            return str(dataset_dir), 0

        vector_store = Chroma(
            collection_name=self.collection_name,
            persist_directory=str(dataset_dir),
            embedding_function=self._get_embeddings(),
        )
        vector_store.add_documents(chunked_documents)
        return str(dataset_dir), len(chunked_documents)

    def sync_data_directory(self, data_dir: str) -> SyncReport:
        """
        Incrementally synchronize JSON files under data directory into Chroma.

        Args:
            data_dir (str): Directory path containing source JSON knowledge files.

        Returns:
            SyncReport: Added/updated/removed/skipped files and indexed chunk count.

        The method detects file add/remove/content-change and indexes only affected files.
        """

        current_files = self._scan_json_files(data_dir)
        previous_state = self._load_state_map()

        report = SyncReport(
            added_files=[],
            updated_files=[],
            removed_files=[],
            skipped_files=[],
            indexed_chunks=0,
        )

        previous_paths = set(previous_state.keys())
        current_paths = set(current_files.keys())

        removed_paths = sorted(previous_paths - current_paths)
        for relative_path in removed_paths:
            state = previous_state[relative_path]
            removed_dataset_dir = Path(state.dataset_dir)
            if removed_dataset_dir.exists():
                shutil.rmtree(removed_dataset_dir, ignore_errors=True)
            self._delete_state_entry(relative_path)
            report.removed_files.append(relative_path)

        for relative_path in sorted(current_paths):
            file_path = current_files[relative_path]
            try:
                content_hash = self._compute_content_hash(file_path)
            except OSError:
                logger.exception("Failed to hash file during RAG sync: %s", file_path)
                report.skipped_files.append(relative_path)
                continue

            previous = previous_state.get(relative_path)
            should_rebuild = (
                previous is None
                or previous.content_hash != content_hash
                or not Path(previous.dataset_dir).exists()
            )
            if not should_rebuild:
                continue

            try:
                rebuild_result = self._rebuild_file_index(
                    file_path=file_path,
                    relative_file_path=relative_path,
                )
                indexed_dataset_dir = str(rebuild_result[0])
                chunk_count = int(rebuild_result[1])
                self._upsert_state_entry(
                    file_path=relative_path,
                    content_hash=content_hash,
                    dataset_dir=indexed_dataset_dir,
                )
                report.indexed_chunks += chunk_count
                if previous is None:
                    report.added_files.append(relative_path)
                else:
                    report.updated_files.append(relative_path)
            except (json.JSONDecodeError, OSError, RuntimeError, ValueError, sqlite3.Error):
                logger.exception("Failed to index file during RAG sync: %s", file_path)
                report.skipped_files.append(relative_path)

        return report

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
        """
        Split plain text into overlapping chunks.

        Args:
            text (str): Raw text to split.
            chunk_size (int): Target chunk size, valid range is integers >= 1.
            overlap (int): Overlap size, valid range is integers >= 0.

        Returns:
            list[str]: Chunked text list.

        This method preserves backward compatibility with the previous RAG API.
        """

        text = text.strip()
        if not text:
            return []
        if len(text) <= chunk_size:
            return [text]

        chunks: List[str] = []
        start = 0
        step = max(1, chunk_size - overlap)
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start += step
        return chunks

    def add_documents(self, docs: Iterable[str], source: str) -> int:
        """
        Add plain text documents into a dedicated per-source Chroma dataset.

        Args:
            docs (Iterable[str]): Raw text documents to index.
            source (str): Logical source identifier used as metadata and dataset key.

        Returns:
            int: Number of indexed chunks.

        The method keeps compatibility with old API while using vector indexing.
        """

        normalized_documents: List[Document] = []
        for idx, doc in enumerate(docs):
            normalized = self._normalize_text(doc)
            if normalized:
                normalized_documents.append(
                    Document(
                        page_content=normalized,
                        metadata={"source": source, "record_index": idx},
                    )
                )

        chunked_documents = self._split_documents(normalized_documents)
        if not chunked_documents:
            return 0

        dataset_dir = self._dataset_dir_for_file(source)
        if dataset_dir.exists():
            shutil.rmtree(dataset_dir, ignore_errors=True)

        vector_store = Chroma(
            collection_name=self.collection_name,
            persist_directory=str(dataset_dir),
            embedding_function=self._get_embeddings(),
        )
        vector_store.add_documents(chunked_documents)

        digest = hashlib.md5("\n".join(doc.page_content for doc in chunked_documents).encode("utf-8")).hexdigest()
        self._upsert_state_entry(file_path=source, content_hash=digest, dataset_dir=str(dataset_dir))
        return len(chunked_documents)

    def add_text_file(self, file_path: str, chunk_size: int = 500, overlap: int = 80) -> int:
        """
        Read a plain text file and index it into the vector store.

        Args:
            file_path (str): Existing text file path.
            chunk_size (int): Chunk size for splitting, valid range is integers >= 1.
            overlap (int): Chunk overlap size, valid range is integers >= 0.

        Returns:
            int: Number of indexed chunks.

        This helper is mainly retained for API compatibility and manual ingestion.
        """

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Knowledge file not found: {file_path}")

        text = path.read_text(encoding="utf-8")
        chunks = self._chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        return self.add_documents(chunks, source=str(path))

    @staticmethod
    def _distance_to_score(distance: float) -> int:
        """
        Convert vector distance to an integer relevance score.

        Args:
            distance (float): Non-negative vector distance returned by Chroma.

        Returns:
            int: Positive relevance score where larger means better match.

        The conversion keeps old retrieve API semantics with descending score order.
        """

        safe_distance = max(0.0, float(distance))
        return max(1, int(round(1000.0 / (1.0 + safe_distance))))

    def retrieve(self, query: str, top_k: int = 3) -> List[RetrievalItem]:
        """
        Retrieve top-k relevant chunks from all indexed per-file datasets.

        Args:
            query (str): User query text for semantic search.
            top_k (int): Number of results to return, valid range is integers >= 1.

        Returns:
            list[RetrievalItem]: Ranked retrieval hits sorted by score descending.

        The method aggregates results from all file datasets and applies global ranking.
        """

        query = query.strip()
        if not query:
            return []

        try:
            embeddings = self._get_embeddings()
        except RuntimeError:
            logger.exception("RAG retrieve skipped due to invalid embedding configuration")
            return []

        state_map = self._load_state_map()
        aggregated: List[RetrievalItem] = []
        seq = 1
        per_dataset_k = max(1, top_k)

        for file_path, state in state_map.items():
            dataset_dir = Path(state.dataset_dir)
            if not dataset_dir.exists():
                continue

            try:
                vector_store = Chroma(
                    collection_name=self.collection_name,
                    persist_directory=str(dataset_dir),
                    embedding_function=embeddings,
                )
                rows = vector_store.similarity_search_with_score(query, k=per_dataset_k)
            except (RuntimeError, ValueError, OSError):
                logger.exception("RAG retrieval failed for dataset: %s", dataset_dir)
                continue

            for doc, distance in rows:
                normalized_content = self._normalize_text(doc.page_content)
                if not normalized_content:
                    continue

                source = str(doc.metadata.get("source", file_path))
                aggregated.append(
                    RetrievalItem(
                        id=seq,
                        source=source,
                        content=normalized_content,
                        score=self._distance_to_score(distance),
                    )
                )
                seq += 1

        aggregated.sort(key=lambda item: item.score, reverse=True)

        unique: List[RetrievalItem] = []
        seen: set[tuple[str, str]] = set()
        for item in aggregated:
            signature = (item.source, item.content)
            if signature in seen:
                continue
            seen.add(signature)
            unique.append(item)
            if len(unique) >= max(1, top_k):
                break

        return unique

    def build_context(self, query: str, top_k: int = 3, max_chars: int = 1200) -> str:
        """
        Build an injected context string from top retrieval hits.

        Args:
            query (str): User query text.
            top_k (int): Max number of retrieval hits to include, range integers >= 1.
            max_chars (int): Maximum output character length, range integers >= 1.

        Returns:
            str: Concatenated context text or empty string when no hits found.

        The output is designed to be directly prepended to LLM user content.
        """

        items = self.retrieve(query=query, top_k=top_k)
        if not items:
            return ""

        context_parts: List[str] = []
        current_len = 0
        for idx, item in enumerate(items, start=1):
            piece = f"[知识{idx} | source={item.source}]\n{item.content}"
            if current_len + len(piece) > max_chars:
                break
            context_parts.append(piece)
            current_len += len(piece)

        return "\n\n".join(context_parts)
