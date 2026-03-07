"""
MirAI OS — Unlimited Context Memory System
Three-tier architecture:
  1. Short-term  → Redis (last N messages, fast)
  2. Medium-term → SQLite + LLM compression (summaries)
  3. Long-term   → ChromaDB (semantic vector search, truly unlimited)
Retrieval fuses all three tiers for effectively infinite context.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

from core.config import cfg

logger = logging.getLogger("mirai.memory")

DATA_DIR = Path(cfg.get("system", "data_dir", default="./data"))
DB_PATH = DATA_DIR / "conversations" / "history.db"
VECTOR_DIR = DATA_DIR / "vector_store"


# ── helpers ─────────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _ts() -> str:
    return str(int(_now()))


# ── Short-term: Redis ────────────────────────────────────────────────────────

class ShortTermMemory:
    """Last N messages per session stored in Redis."""

    def __init__(self) -> None:
        self._redis = None
        self.max_msgs = int(cfg.memory.get("short_term", {}).get("max_messages", 50))
        self.ttl = int(cfg.memory.get("short_term", {}).get("ttl", 86400))

    def _r(self):
        if self._redis is None:
            try:
                import redis
                self._redis = redis.from_url(cfg.redis_url, decode_responses=True)
                self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis unavailable ({e}), using in-memory fallback.")
                self._redis = _DictRedis()
        return self._redis

    def _key(self, session_id: str) -> str:
        return f"mirai:session:{session_id}:messages"

    def push(self, session_id: str, role: str, content: str) -> None:
        msg = json.dumps({"role": role, "content": content, "ts": _now()})
        r = self._r()
        r.rpush(self._key(session_id), msg)
        r.expire(self._key(session_id), self.ttl)
        # trim to max
        r.ltrim(self._key(session_id), -self.max_msgs, -1)

    def get_all(self, session_id: str) -> list[dict]:
        r = self._r()
        raw = r.lrange(self._key(session_id), 0, -1)
        msgs = []
        for item in raw:
            try:
                msgs.append(json.loads(item))
            except Exception:
                pass
        return msgs

    def clear(self, session_id: str) -> None:
        self._r().delete(self._key(session_id))

    def count(self, session_id: str) -> int:
        return self._r().llen(self._key(session_id))


class _DictRedis:
    """In-memory fallback when Redis is not available."""

    def __init__(self) -> None:
        self._store: dict[str, list] = {}
        self._expiry: dict[str, float] = {}

    def _check_expired(self, key: str) -> None:
        if key in self._expiry and time.time() > self._expiry[key]:
            self._store.pop(key, None)
            self._expiry.pop(key, None)

    def rpush(self, key: str, value: str) -> None:
        self._check_expired(key)
        self._store.setdefault(key, []).append(value)

    def expire(self, key: str, seconds: int) -> None:
        self._expiry[key] = time.time() + seconds

    def ltrim(self, key: str, start: int, end: int) -> None:
        lst = self._store.get(key, [])
        if start < 0:
            start = max(0, len(lst) + start)
        if end < 0:
            end = len(lst) + end
        self._store[key] = lst[start:end + 1]

    def lrange(self, key: str, start: int, end: int) -> list:
        self._check_expired(key)
        lst = self._store.get(key, [])
        if end == -1:
            return lst[start:]
        return lst[start:end + 1]

    def llen(self, key: str) -> int:
        return len(self._store.get(key, []))

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def ping(self) -> None:
        pass


# ── Medium-term: SQLite + summaries ─────────────────────────────────────────

class MediumTermMemory:
    """Compressed conversation summaries in SQLite."""

    def __init__(self) -> None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._init_db()
        self.summarize_after = int(
            cfg.memory.get("medium_term", {}).get("summarize_after", 20)
        )

    def _init_db(self) -> None:
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS full_history (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                ts REAL NOT NULL
            )
        """)
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_session ON summaries(session_id)")
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_fh_session ON full_history(session_id)")
        self._db.commit()

    def store_message(self, session_id: str, role: str, content: str) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO full_history VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), session_id, role, content, _now()),
        )
        self._db.commit()

    def store_summary(self, session_id: str, summary: str, msg_count: int) -> None:
        self._db.execute(
            "INSERT INTO summaries VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), session_id, summary, msg_count, _now()),
        )
        self._db.commit()

    def get_summaries(self, session_id: str, limit: int = 5) -> list[str]:
        rows = self._db.execute(
            "SELECT summary FROM summaries WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [r[0] for r in reversed(rows)]

    def get_history(self, session_id: str, limit: int = 100) -> list[dict]:
        rows = self._db.execute(
            "SELECT role, content, ts FROM full_history WHERE session_id=? ORDER BY ts DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [{"role": r[0], "content": r[1], "ts": r[2]} for r in reversed(rows)]

    def needs_summary(self, session_id: str) -> bool:
        count = self._db.execute(
            "SELECT COUNT(*) FROM full_history WHERE session_id=?", (session_id,)
        ).fetchone()[0]
        summary_count = self._db.execute(
            "SELECT COALESCE(SUM(message_count),0) FROM summaries WHERE session_id=?",
            (session_id,),
        ).fetchone()[0]
        return (count - summary_count) >= self.summarize_after


# ── Long-term: ChromaDB vector store ────────────────────────────────────────

class LongTermMemory:
    """Semantic vector memory — effectively unlimited context via retrieval."""

    def __init__(self) -> None:
        self._chroma = None
        self._collection = None
        self._embed_model = None
        VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    def _init(self) -> None:
        if self._chroma is not None:
            return
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self._chroma = chromadb.PersistentClient(
                path=str(VECTOR_DIR),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._chroma.get_or_create_collection(
                name=cfg.memory.get("long_term", {}).get("collection", "mirai_longterm"),
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")

    def _embed(self, text: str) -> list[float]:
        if self._embed_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                model_name = cfg.memory.get("long_term", {}).get(
                    "embed_model", "all-MiniLM-L6-v2"
                )
                self._embed_model = SentenceTransformer(model_name)
            except Exception as e:
                logger.error(f"Embedding model load failed: {e}")
                return []
        return self._embed_model.encode(text).tolist()

    def store(self, session_id: str, role: str, content: str, metadata: dict | None = None) -> None:
        self._init()
        if self._collection is None:
            return
        try:
            doc_id = f"{session_id}_{_ts()}_{uuid.uuid4().hex[:8]}"
            embedding = self._embed(content)
            if not embedding:
                return
            meta = {"session_id": session_id, "role": role, "ts": _now()}
            if metadata:
                meta.update(metadata)
            self._collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[meta],
            )
        except Exception as e:
            logger.error(f"Vector store error: {e}")

    def retrieve(self, query: str, session_id: Optional[str] = None, top_k: int = 10) -> list[str]:
        self._init()
        if self._collection is None:
            return []
        try:
            embedding = self._embed(query)
            if not embedding:
                return []
            where = {"session_id": session_id} if session_id else None
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, self._collection.count() or 1),
                where=where,
            )
            return results.get("documents", [[]])[0]
        except Exception as e:
            logger.error(f"Vector retrieve error: {e}")
            return []


# ── Unified Memory Manager ────────────────────────────────────────────────────

class MemoryManager:
    """
    Unified interface fusing all three memory tiers.
    Provides build_context() to construct an LLM-ready message list
    with unlimited effective context.
    """

    def __init__(self) -> None:
        self.short = ShortTermMemory()
        self.medium = MediumTermMemory()
        self.long = LongTermMemory()
        # Optional cloud backends (loaded lazily)
        self._qdrant = None
        self._mem0 = None

    def _get_qdrant(self):
        if self._qdrant is None:
            try:
                from integrations.qdrant_store import qdrant
                self._qdrant = qdrant if qdrant.is_available() else False
            except Exception:
                self._qdrant = False
        return self._qdrant if self._qdrant else None

    def _get_mem0(self):
        if self._mem0 is None:
            try:
                from integrations.mem0_memory import mem0
                self._mem0 = mem0 if mem0.is_available() else False
            except Exception:
                self._mem0 = False
        return self._mem0 if self._mem0 else None

    def record(self, session_id: str, role: str, content: str) -> None:
        """Store a message in all applicable tiers (local + optional cloud)."""
        self.short.push(session_id, role, content)
        self.medium.store_message(session_id, role, content)
        self.long.store(session_id, role, content)
        # Cloud backends (async, fire-and-forget)
        import asyncio
        qdrant = self._get_qdrant()
        if qdrant:
            asyncio.create_task(qdrant.store(session_id, role, content))
        mem0 = self._get_mem0()
        if mem0:
            asyncio.create_task(
                mem0.add([{"role": role, "content": content}], session_id=session_id)
            )

    async def maybe_compress(self, session_id: str, llm_client) -> None:
        """If enough new messages have accumulated, compress into a summary."""
        if not self.medium.needs_summary(session_id):
            return
        recent = self.medium.get_history(session_id, limit=40)
        if not recent:
            return

        # Build prompt for summarization
        conv_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in recent
        )
        summary_prompt = [
            {
                "role": "system",
                "content": (
                    "You are a memory compression system. "
                    "Summarize the following conversation concisely, preserving all key facts, "
                    "decisions, tasks, and context. Be precise and complete."
                ),
            },
            {"role": "user", "content": f"Compress this conversation:\n\n{conv_text}"},
        ]
        try:
            summary = await llm_client.complete(summary_prompt, temperature=0.3, max_tokens=1024)
            self.medium.store_summary(session_id, summary, len(recent))
            logger.info(f"Compressed {len(recent)} messages into summary for {session_id}")
        except Exception as e:
            logger.error(f"Compression failed: {e}")

    def build_context(
        self,
        session_id: str,
        current_query: str,
        system_prompt: str,
        max_tokens: int = 28000,
    ) -> list[dict]:
        """
        Build a full message list for LLM consumption.
        Order: system → relevant long-term memories → summaries → recent messages.
        """
        messages: list[dict] = [{"role": "system", "content": system_prompt}]

        # Long-term relevant memories — try Qdrant cloud first, then local ChromaDB
        qdrant = self._get_qdrant()
        if qdrant:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                relevant = loop.run_until_complete(qdrant.retrieve(current_query, session_id=session_id, top_k=8))
            except Exception:
                relevant = self.long.retrieve(current_query, session_id=session_id, top_k=8)
        else:
            relevant = self.long.retrieve(current_query, session_id=session_id, top_k=8)

        # Also check Mem0 cloud memories
        mem0 = self._get_mem0()
        if mem0:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                cloud_mems = loop.run_until_complete(mem0.search_formatted(current_query))
                if cloud_mems:
                    messages.append({"role": "system", "content": cloud_mems})
            except Exception:
                pass

        if relevant:
            memory_text = "\n---\n".join(relevant[:5])
            messages.append({
                "role": "system",
                "content": f"[RELEVANT MEMORIES FROM PAST SESSIONS]\n{memory_text}",
            })

        # Medium-term summaries
        summaries = self.medium.get_summaries(session_id, limit=3)
        if summaries:
            summary_text = "\n\n".join(summaries)
            messages.append({
                "role": "system",
                "content": f"[CONVERSATION HISTORY SUMMARY]\n{summary_text}",
            })

        # Short-term: recent messages
        recent = self.short.get_all(session_id)
        for msg in recent:
            messages.append({"role": msg["role"], "content": msg["content"]})

        return messages


# Global singleton
memory = MemoryManager()
