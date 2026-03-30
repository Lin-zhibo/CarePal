from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List


@dataclass
class RetrievalItem:
    id: int
    source: str
    content: str
    score: int


class SimpleRAGStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip())

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
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
        now = datetime.utcnow().isoformat()
        rows = []
        for doc in docs:
            normalized = self._normalize_text(doc)
            if normalized:
                rows.append((source, normalized, now))
        if not rows:
            return 0
        self.conn.executemany(
            "INSERT INTO knowledge_docs (source, content, created_at) VALUES (?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def add_text_file(self, file_path: str, chunk_size: int = 500, overlap: int = 80) -> int:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Knowledge file not found: {file_path}")
        text = path.read_text(encoding="utf-8")
        chunks = self._chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        return self.add_documents(chunks, source=str(path))

    @staticmethod
    def _tokenize_for_score(query: str) -> List[str]:
        q = query.strip().lower()
        if not q:
            return []

        words = re.findall(r"[a-z0-9_]+", q)
        cjk_chars = re.findall(r"[\u4e00-\u9fff]", q)
        cjk_bigrams = ["".join(cjk_chars[i : i + 2]) for i in range(max(0, len(cjk_chars) - 1))]

        tokens = set(words + cjk_bigrams)
        compact = re.sub(r"\s+", "", q)
        if len(compact) >= 2:
            tokens.add(compact)
        return [tok for tok in tokens if tok]

    @classmethod
    def _score(cls, query: str, content: str) -> int:
        if not query or not content:
            return 0

        q = query.strip().lower()
        c = content.lower()
        score = 0
        if q and q in c:
            score += 6

        for token in cls._tokenize_for_score(query):
            if token in c:
                if len(token) >= 4:
                    score += 3
                else:
                    score += 1
        return score

    def retrieve(self, query: str, top_k: int = 3) -> List[RetrievalItem]:
        query = query.strip()
        if not query:
            return []

        rows = self.conn.execute("SELECT id, source, content FROM knowledge_docs").fetchall()
        scored: List[RetrievalItem] = []
        for row in rows:
            score = self._score(query, row[2])
            if score > 0:
                scored.append(RetrievalItem(id=row[0], source=row[1], content=row[2], score=score))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[: max(1, top_k)]

    def build_context(self, query: str, top_k: int = 3, max_chars: int = 1200) -> str:
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
