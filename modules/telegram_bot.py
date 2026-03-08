"""
Telegram Bot Module – Okabe personality-driven bot.
Handles incoming messages and routes them through the LLM engine.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from modules.llm_engine import LLMEngine

import config

logger = logging.getLogger(__name__)

# Per-user chat history (simple in-memory store)
_history: dict[int, list] = {}


class TelegramBot:
    """Telegram bot with Okabe personality powered by LLMEngine."""

    def __init__(self, llm: "LLMEngine") -> None:
        self.llm = llm
        self.token = config.TELEGRAM_BOT_TOKEN
        self._app: Optional[object] = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start polling. Blocks until stopped."""
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not set – bot disabled.")
            return
        try:
            from telegram import Update  # type: ignore
            from telegram.ext import (  # type: ignore
                Application,
                CommandHandler,
                MessageHandler,
                filters,
            )
        except ImportError:
            logger.error("python-telegram-bot not installed.")
            return

        app = (
            Application.builder()
            .token(self.token)
            .build()
        )
        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("reset", self._cmd_reset))
        app.add_handler(CommandHandler("mod2", self._cmd_mod2))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
        )
        self._app = app
        logger.info("Telegram bot starting…")
        app.run_polling(drop_pending_updates=True)

    def stop(self) -> None:
        if self._app is not None:
            try:
                self._app.stop()  # type: ignore[attr-defined]
            except Exception:
                pass

    # ── handlers ──────────────────────────────────────────────────────────────

    async def _cmd_start(self, update, context) -> None:  # type: ignore
        uid = update.effective_user.id
        _history[uid] = []
        await update.message.reply_text(
            "El Psy Kongroo! I am Hououin Kyouma. "
            "The Organization will not silence my research. "
            "How may I assist you, lab member?"
        )

    async def _cmd_reset(self, update, context) -> None:  # type: ignore
        uid = update.effective_user.id
        _history[uid] = []
        await update.message.reply_text("Memory purged. A fresh experiment begins.")

    async def _cmd_mod2(self, update, context) -> None:  # type: ignore
        await update.message.reply_text(
            "Mod 2 engaged! Advanced cognitive systems online. "
            "Memory, web search, and deep-agent capabilities are active."
        )

    async def _on_message(self, update, context) -> None:  # type: ignore
        uid = update.effective_user.id
        text = update.message.text
        history = _history.setdefault(uid, [])
        reply = self.llm.chat(text, history=history)
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": reply})
        # Keep last 20 turns to avoid context overflow
        _history[uid] = history[-40:]
        await update.message.reply_text(reply)
