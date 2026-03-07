"""
MirAI OS — Mem0 Cloud Memory Integration (Optional)
Mem0 is a persistent, intelligent memory layer for AI.
Syncs MirAI's memory to the cloud — survives reinstalls.
Free tier: Available at mem0.ai

Enable: set MEM0_API_KEY in .env
        set integrations.mem0.enabled: true in settings.yaml

Without Mem0: Memory is local-only (ChromaDB + SQLite).
With Mem0:    Memory syncs to cloud — access from any device.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("mirai.integrations.mem0")


class Mem0Memory:
    """Cloud memory layer via Mem0."""

    def __init__(self) -> None:
        self.api_key = os.getenv("MEM0_API_KEY", "")
        self.enabled = bool(self.api_key)
        self._client = None
        self._user_id = "mirai_os_default"

    def is_available(self) -> bool:
        return self.enabled

    def _get_client(self):
        if self._client is None:
            try:
                from mem0 import MemoryClient
                self._client = MemoryClient(api_key=self.api_key)
            except ImportError:
                logger.error("mem0ai not installed. Run: pip install mem0ai")
                raise
        return self._client

    async def add(self, messages: list[dict], session_id: str = "default") -> None:
        """Add messages to Mem0 cloud memory."""
        if not self.is_available():
            return
        try:
            import asyncio
            client = self._get_client()
            await asyncio.to_thread(
                client.add,
                messages,
                user_id=self._user_id,
                metadata={"session_id": session_id},
            )
        except Exception as e:
            logger.error(f"Mem0 add error: {e}")

    async def search(self, query: str, session_id: Optional[str] = None, limit: int = 10) -> list[dict]:
        """Search cloud memories."""
        if not self.is_available():
            return []
        try:
            import asyncio
            client = self._get_client()
            filters = {}
            if session_id:
                filters["metadata"] = {"session_id": session_id}
            results = await asyncio.to_thread(
                client.search,
                query,
                user_id=self._user_id,
                limit=limit,
                filters=filters if filters else None,
            )
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.error(f"Mem0 search error: {e}")
            return []

    async def get_all(self, session_id: Optional[str] = None) -> list[dict]:
        """Get all cloud memories."""
        if not self.is_available():
            return []
        try:
            import asyncio
            client = self._get_client()
            results = await asyncio.to_thread(client.get_all, user_id=self._user_id)
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.error(f"Mem0 get_all error: {e}")
            return []

    async def delete_all(self) -> None:
        """Clear all cloud memories (use carefully!)."""
        if not self.is_available():
            return
        try:
            import asyncio
            client = self._get_client()
            await asyncio.to_thread(client.delete_all, user_id=self._user_id)
            logger.info("All Mem0 cloud memories deleted.")
        except Exception as e:
            logger.error(f"Mem0 delete error: {e}")

    async def search_formatted(self, query: str) -> str:
        """Return search results as formatted text for LLM."""
        results = await self.search(query, limit=5)
        if not results:
            return ""
        lines = ["[CLOUD MEMORIES]"]
        for r in results:
            mem = r.get("memory", r.get("text", str(r)))
            lines.append(f"▸ {mem[:200]}")
        return "\n".join(lines)


# Global singleton
mem0 = Mem0Memory()
