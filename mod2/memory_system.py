"""
Mod 2 – Memory System
Persistent semantic memory for the advanced agent.
Stores and retrieves memories using simple keyword-based search
with optional vector similarity (if sentence-transformers is available).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import config

logger = logging.getLogger(__name__)


class MemorySystem:
    """Persistent key-value memory with keyword-based retrieval."""

    def __init__(self, path: str = config.MOD2_MEMORY_PATH) -> None:
        self.path = Path(path)
        self.max_entries = config.MOD2_MAX_MEMORY
        self._memories: list[dict] = []
        self._next_id: int = 0
        self._load()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def store(self, content: str, tags: Optional[List[str]] = None) -> None:
        """Store a new memory entry."""
        entry = {
            "id": self._next_id,
            "content": content,
            "tags": tags or [],
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
        self._next_id += 1
        self._memories.append(entry)
        # Trim to max entries (keep newest)
        if len(self._memories) > self.max_entries:
            self._memories = self._memories[-self.max_entries:]
        self._save()
        logger.debug("Memory stored (total=%d)", len(self._memories))

    def search(self, query: str, top_k: int = 5) -> List[str]:
        """Return top-k memories relevant to the query."""
        if not self._memories:
            return []

        # Try vector search first
        if self._has_sentence_transformers():
            return self._vector_search(query, top_k)

        # Fallback: keyword overlap
        return self._keyword_search(query, top_k)

    def forget(self, query: str) -> int:
        """Remove memories matching the query. Returns number removed."""
        before = len(self._memories)
        keywords = set(re.findall(r"\w+", query.lower()))
        self._memories = [
            m for m in self._memories
            if not keywords & set(re.findall(r"\w+", m["content"].lower()))
        ]
        removed = before - len(self._memories)
        if removed:
            self._save()
        return removed

    def all(self) -> List[dict]:
        return list(self._memories)

    def clear(self) -> None:
        self._memories = []
        self._save()

    # ── search backends ───────────────────────────────────────────────────────

    def _keyword_search(self, query: str, top_k: int) -> List[str]:
        query_words = set(re.findall(r"\w+", query.lower()))
        scored: list[tuple[float, str]] = []
        for m in self._memories:
            mem_words = set(re.findall(r"\w+", m["content"].lower()))
            overlap = len(query_words & mem_words)
            if overlap:
                scored.append((overlap, m["content"]))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [content for _, content in scored[:top_k]]

    def _has_sentence_transformers(self) -> bool:
        try:
            import sentence_transformers  # noqa: F401

            return True
        except ImportError:
            return False

    def _vector_search(self, query: str, top_k: int) -> List[str]:
        try:
            from sentence_transformers import SentenceTransformer, util  # type: ignore

            model = SentenceTransformer("all-MiniLM-L6-v2")
            corpus = [m["content"] for m in self._memories]
            query_emb = model.encode(query, convert_to_tensor=True)
            corpus_emb = model.encode(corpus, convert_to_tensor=True)
            hits = util.semantic_search(query_emb, corpus_emb, top_k=top_k)[0]
            return [corpus[h["corpus_id"]] for h in hits]
        except Exception as exc:
            logger.warning("Vector search failed, falling back to keyword: %s", exc)
            return self._keyword_search(query, top_k)

    # ── persistence ───────────────────────────────────────────────────────────

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._memories, indent=2))

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._memories = json.loads(self.path.read_text())
                # Restore _next_id to avoid ID collisions after loading
                self._next_id = max((m.get("id", 0) for m in self._memories), default=-1) + 1
                logger.info("Memory loaded: %d entries", len(self._memories))
            except Exception as exc:
                logger.error("Failed to load memory: %s", exc)
                self._memories = []
        else:
            self._memories = []
