"""
MirAI OS — Qdrant Vector Store Integration (Optional)
Qdrant Cloud provides managed vector storage — scales beyond local ChromaDB.
Free tier: 1GB storage at cloud.qdrant.io

Enable: set QDRANT_URL and QDRANT_API_KEY in .env
        set integrations.qdrant.enabled: true in settings.yaml

Without Qdrant: MirAI uses local ChromaDB (./data/vector_store).
With Qdrant:    Vectors stored in cloud — survives reinstalls, scales infinitely.
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Optional

logger = logging.getLogger("mirai.integrations.qdrant")

COLLECTION_NAME = "mirai_longterm"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 output dim


class QdrantStore:
    """Cloud-backed vector store via Qdrant."""

    def __init__(self) -> None:
        self.url = os.getenv("QDRANT_URL", "")
        self.api_key = os.getenv("QDRANT_API_KEY", "")
        self.enabled = bool(self.url and self.api_key)
        self._client = None
        self._embed_model = None

    def is_available(self) -> bool:
        return self.enabled

    def _get_client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                self._client = QdrantClient(url=self.url, api_key=self.api_key)
                # Ensure collection exists
                from qdrant_client.models import Distance, VectorParams
                existing = [c.name for c in self._client.get_collections().collections]
                if COLLECTION_NAME not in existing:
                    self._client.create_collection(
                        collection_name=COLLECTION_NAME,
                        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                    )
                    logger.info(f"Qdrant collection '{COLLECTION_NAME}' created.")
            except ImportError:
                logger.error("qdrant-client not installed. Run: pip install qdrant-client")
                raise
        return self._client

    def _get_embed(self):
        if self._embed_model is None:
            from sentence_transformers import SentenceTransformer
            self._embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embed_model

    async def store(self, session_id: str, role: str, content: str, metadata: Optional[dict] = None) -> None:
        """Store a message as a vector in Qdrant cloud."""
        if not self.is_available():
            return
        try:
            import asyncio
            from qdrant_client.models import PointStruct

            embedding = await asyncio.to_thread(
                self._get_embed().encode, content
            )
            client = self._get_client()
            meta = {"session_id": session_id, "role": role, "ts": time.time(), "content": content}
            if metadata:
                meta.update(metadata)

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding.tolist(),
                payload=meta,
            )
            await asyncio.to_thread(
                client.upsert,
                collection_name=COLLECTION_NAME,
                points=[point],
            )
        except Exception as e:
            logger.error(f"Qdrant store error: {e}")

    async def retrieve(self, query: str, session_id: Optional[str] = None, top_k: int = 8) -> list[str]:
        """Semantic search — retrieve relevant memories from cloud."""
        if not self.is_available():
            return []
        try:
            import asyncio
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            embedding = await asyncio.to_thread(self._get_embed().encode, query)
            client = self._get_client()

            query_filter = None
            if session_id:
                query_filter = Filter(
                    must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]
                )

            results = await asyncio.to_thread(
                client.search,
                collection_name=COLLECTION_NAME,
                query_vector=embedding.tolist(),
                query_filter=query_filter,
                limit=top_k,
            )
            return [r.payload.get("content", "") for r in results if r.payload]
        except Exception as e:
            logger.error(f"Qdrant retrieve error: {e}")
            return []

    async def count(self) -> int:
        """Return total vectors stored."""
        if not self.is_available():
            return 0
        try:
            import asyncio
            client = self._get_client()
            info = await asyncio.to_thread(client.get_collection, COLLECTION_NAME)
            return info.points_count or 0
        except Exception:
            return 0


# Global singleton
qdrant = QdrantStore()
