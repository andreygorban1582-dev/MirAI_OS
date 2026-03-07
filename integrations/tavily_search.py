"""
MirAI OS — Tavily Search Integration (Optional)
Tavily is an AI-optimized search API with clean, structured results.
Much better than scraping DuckDuckGo for research tasks.
Free tier: 1,000 searches/month

Enable: set TAVILY_API_KEY in .env
        set integrations.tavily.enabled: true in settings.yaml

Without Tavily: MirAI uses Playwright + DuckDuckGo scraping.
With Tavily:    MirAI gets clean, structured search results.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("mirai.integrations.tavily")


class TavilySearch:
    """Tavily AI search — structured, reliable results."""

    def __init__(self) -> None:
        self.api_key = os.getenv("TAVILY_API_KEY", "")
        self.enabled = bool(self.api_key)
        self._http = None

    def is_available(self) -> bool:
        return self.enabled

    def _get_http(self):
        if self._http is None:
            import httpx
            self._http = httpx.AsyncClient(timeout=30)
        return self._http

    async def search(
        self,
        query: str,
        search_depth: str = "basic",   # "basic" | "advanced"
        max_results: int = 8,
        include_raw_content: bool = False,
        include_answer: bool = True,   # Get AI-synthesized answer
        topic: str = "general",       # "general" | "news"
    ) -> dict:
        """
        Search the web. Returns:
        {
            "answer": "AI-synthesized answer",
            "results": [{"title": ..., "url": ..., "content": ..., "score": ...}],
            "query": "original query"
        }
        """
        if not self.is_available():
            raise RuntimeError("Tavily not configured — add TAVILY_API_KEY to .env")

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_raw_content": include_raw_content,
            "include_answer": include_answer,
            "topic": topic,
        }

        http = self._get_http()
        try:
            resp = await http.post("https://api.tavily.com/search", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return {"answer": "", "results": [], "query": query, "error": str(e)}

    async def search_formatted(self, query: str, max_results: int = 5) -> str:
        """Search and return formatted text for LLM consumption."""
        data = await self.search(query, max_results=max_results)
        lines = []

        if data.get("answer"):
            lines.append(f"**Summary:** {data['answer']}\n")

        for i, r in enumerate(data.get("results", []), 1):
            lines.append(f"{i}. **{r.get('title', 'Result')}**")
            lines.append(f"   {r.get('url', '')}")
            lines.append(f"   {r.get('content', '')[:300]}")
            lines.append("")

        return "\n".join(lines) if lines else "No results found."

    async def news_search(self, query: str, max_results: int = 5) -> str:
        """Search for recent news."""
        data = await self.search(query, topic="news", max_results=max_results, search_depth="advanced")
        return await self.search_formatted.__func__(self, query, max_results)

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()


# Global singleton
tavily = TavilySearch()
