"""
Context Optimizer – manages and compresses conversation history to stay
within LLM context window limits.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from modules.llm_engine import LLMEngine

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = (
    "Summarize the following conversation history in a concise paragraph "
    "preserving all important facts, decisions, and context:\n\n{history}"
)


class ContextOptimizer:
    """Manages token-efficient conversation context for long sessions."""

    MAX_TURNS = 20
    COMPRESS_AT = 30

    def __init__(self, llm: Optional["LLMEngine"] = None) -> None:
        self.llm = llm
        self._history: List[dict] = []
        self._summary: str = ""

    # ── public API ────────────────────────────────────────────────────────────

    def add(self, role: str, content: str) -> None:
        """Append a message and compress if needed."""
        self._history.append({"role": role, "content": content})
        if len(self._history) >= self.COMPRESS_AT:
            self._compress()

    def get_history(self) -> List[dict]:
        """Return the current (possibly compressed) history."""
        if self._summary:
            prefix = [{"role": "system", "content": f"[Summary] {self._summary}"}]
            return prefix + self._history
        return list(self._history)

    def clear(self) -> None:
        self._history = []
        self._summary = ""

    def token_estimate(self) -> int:
        """Rough token estimate (4 chars ≈ 1 token)."""
        total = sum(len(m["content"]) for m in self._history)
        total += len(self._summary)
        return total // 4

    # ── compression ───────────────────────────────────────────────────────────

    def _compress(self) -> None:
        """Summarize the older half of the history to save context."""
        split = len(self._history) // 2
        to_summarize = self._history[:split]
        self._history = self._history[split:]

        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in to_summarize
        )
        if self.llm:
            try:
                new_summary = self.llm.chat(
                    SUMMARY_PROMPT.format(history=history_text),
                    system="You are a helpful summarizer.",
                )
                if self._summary:
                    self._summary = f"{self._summary}\n{new_summary}"
                else:
                    self._summary = new_summary
                logger.debug("Context compressed. Summary length: %d", len(self._summary))
                return
            except Exception as exc:
                logger.warning("LLM summarization failed: %s", exc)
        # Fallback: just keep a raw truncated version
        self._summary = history_text[:500] + "…"

    # ── persistence ───────────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        data = {"summary": self._summary, "history": self._history}
        Path(path).write_text(json.dumps(data, indent=2))

    def load(self, path: str) -> None:
        try:
            data = json.loads(Path(path).read_text())
            self._summary = data.get("summary", "")
            self._history = data.get("history", [])
        except Exception as exc:
            logger.error("Failed to load context from %s: %s", path, exc)
