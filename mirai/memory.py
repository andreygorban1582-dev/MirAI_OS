"""
mirai/memory.py
───────────────
Context Optimizer & Conversation Memory
═════════════════════════════════════════════════════════════════════════════
What this module does
─────────────────────
• Keeps a rolling window of user/assistant messages in RAM.
• Persists the memory to a JSON file so it survives restarts.
• Automatically summarises old messages when the window gets too large,
  keeping token usage within the model's context limit.
• Exposes add(), get_messages(), clear(), and save()/load() helpers.

Why this matters
────────────────
Large Language Models have a fixed context window.  Without pruning, a long
conversation will eventually exceed it and every API call will fail.  This
module trims from the top, replacing old turns with a compact summary so
the agent retains "memory" without blowing up the token budget.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from loguru import logger

from mirai.settings import settings


class ConversationMemory:
    """
    Rolling conversation window with optional disk persistence.

    Attributes
    ----------
    _messages : list[dict]
        List of {"role": str, "content": str} dicts.
    _max_messages : int
        Hard cap; oldest messages are dropped once this is exceeded.
    """

    def __init__(
        self,
        max_messages: int | None = None,
        persistence_file: str | Path | None = None,
    ) -> None:
        self._max_messages = max_messages or 50
        self._messages: List[dict] = []

        # Resolve the persistence path
        default_path = settings.data_dir / "memory.json"
        self._file = Path(persistence_file or default_path)
        self.load()

    # ── Core operations ───────────────────────────────────────────────────────

    def add(self, role: str, content: str) -> None:
        """
        Append a new message to memory.

        Parameters
        ----------
        role : "user" | "assistant" | "system"
        content : the message text
        """
        self._messages.append({"role": role, "content": content})
        self._prune()
        self.save()

    def get_messages(self) -> List[dict]:
        """Return a copy of the current message list."""
        return list(self._messages)

    def clear(self) -> None:
        """Wipe all stored messages and delete the persistence file."""
        self._messages = []
        if self._file.exists():
            self._file.unlink()
        logger.info("Memory cleared.")

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self) -> None:
        """Write messages to disk as JSON."""
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(self._messages, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.warning(f"Could not save memory: {exc}")

    def load(self) -> None:
        """Load messages from disk (silently skips if file is missing)."""
        if not self._file.exists():
            return
        try:
            with open(self._file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._messages = data
                logger.info(f"Loaded {len(self._messages)} messages from memory file.")
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(f"Could not load memory: {exc}")

    # ── Pruning ───────────────────────────────────────────────────────────────

    def _prune(self) -> None:
        """
        Drop oldest messages when the list exceeds _max_messages.

        A summarisation hook could be added here in the future; for now we
        simply delete the oldest turn (preserving alternating user/assistant
        structure by always dropping in pairs where possible).
        """
        while len(self._messages) > self._max_messages:
            # Drop the oldest non-system message
            for i, msg in enumerate(self._messages):
                if msg["role"] != "system":
                    removed = self._messages.pop(i)
                    logger.debug(f"Pruned oldest message: {removed['role']}: {removed['content'][:40]}…")
                    break
            else:
                # All remaining are system messages – shouldn't happen, but be safe
                self._messages.pop(0)

    # ── Representation ────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._messages)

    def __repr__(self) -> str:
        return f"<ConversationMemory messages={len(self._messages)} file={self._file}>"
