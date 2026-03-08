"""
Mod 2 – Web Scraper
Provides web search and page-fetching capabilities for the advanced agent.
Uses DuckDuckGo for privacy-respecting searches.
"""

from __future__ import annotations

import html
import logging
import re
import urllib.parse
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
_DEFAULT_TIMEOUT = 15


class WebScraper:
    """Web search and page-fetch utilities for MirAI_OS Mod 2."""

    # ── search ────────────────────────────────────────────────────────────────

    def search(self, query: str, max_results: int = 5) -> str:
        """Search DuckDuckGo and return a summary of results."""
        try:
            from duckduckgo_search import DDGS  # type: ignore

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return "No results found."
            lines = []
            for r in results:
                title = r.get("title", "")
                body = r.get("body", "")
                href = r.get("href", "")
                lines.append(f"• {title}\n  {body[:200]}\n  URL: {href}")
            return "\n\n".join(lines)
        except ImportError:
            logger.warning("duckduckgo_search not installed – trying fallback.")
            return self._ddg_html_search(query, max_results)
        except Exception as exc:
            logger.error("Search error: %s", exc)
            return f"Search error: {exc}"

    # ── page fetch ────────────────────────────────────────────────────────────

    def fetch(self, url: str, max_chars: int = 3000) -> str:
        """Fetch a URL and return cleaned text content."""
        if not url.startswith(("http://", "https://")):
            return f"Invalid URL: {url}"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": _USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT) as resp:  # noqa: S310
                content_type = resp.headers.get("Content-Type", "")
                if "text" not in content_type:
                    return f"Non-text content type: {content_type}"
                raw = resp.read(1024 * 64).decode(errors="replace")
        except Exception as exc:
            return f"Fetch error: {exc}"

        return self._extract_text(raw)[:max_chars]

    # ── helpers ───────────────────────────────────────────────────────────────

    def _ddg_html_search(self, query: str, max_results: int) -> str:
        """Minimal HTML-based DuckDuckGo fallback (no JavaScript)."""
        encoded = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        raw = self.fetch(url, max_chars=8000)
        return raw[:2000] if raw else "Search unavailable."

    @staticmethod
    def _extract_text(html_str: str) -> str:
        """Strip HTML tags and decode entities."""
        # Remove script/style blocks
        html_str = re.sub(
            r"<(script|style|head)[^>]*>.*?</\1>", "", html_str,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Remove remaining tags
        html_str = re.sub(r"<[^>]+>", " ", html_str)
        # Decode HTML entities
        html_str = html.unescape(html_str)
        # Collapse whitespace
        html_str = re.sub(r"\s+", " ", html_str).strip()
        return html_str
