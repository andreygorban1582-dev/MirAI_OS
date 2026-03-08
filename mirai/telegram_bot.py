"""
mirai/telegram_bot.py
─────────────────────
Telegram Bot – Okabe Personality Interface
═════════════════════════════════════════════════════════════════════════════
What this module does
─────────────────────
• Runs an async Telegram bot using python-telegram-bot v21+.
• Every incoming message is forwarded to the Agent for processing.
• The reply is sent back to the user with Markdown formatting.
• Special /commands give the user direct control over agent functions:
    /start   – greet the user, show capabilities
    /status  – show current IP (via Tor), memory size, voice status
    /run     – execute a shell command on the Kali host
    /memory  – dump the last N conversation messages
    /selfmod – trigger a self-modification cycle
    /anon    – rotate Tor identity and report new IP
    /voice   – toggle voice mode on/off
• Access control: if TELEGRAM_ALLOWED_USERS is set, only those user IDs can
  interact with the bot (all others receive a polite rejection).

Okabe Personality
─────────────────
When a message contains one of the "okabe_triggers" from config.yaml (e.g.
"El Psy Congroo"), MirAI responds with a dramatic Steins;Gate catchphrase
before continuing normally.  This flavours the interface without affecting
the underlying intelligence.
"""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING, Optional

from loguru import logger
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from mirai.settings import settings

if TYPE_CHECKING:
    from mirai.agent import Agent


class TelegramBot:
    """
    Telegram interface for MirAI.

    Parameters
    ----------
    agent : Agent
        The running Agent instance to forward messages to.
    token : str, optional
        Override the Telegram bot token from settings.
    """

    def __init__(self, agent: "Agent", token: str | None = None) -> None:
        self._agent = agent
        self._token = token or settings.telegram_token
        self._allowed_users: list[int] = settings.telegram_allowed_users
        self._okabe_triggers: list[str] = settings.okabe_triggers
        self._catchphrases: list[str] = settings.okabe_catchphrases
        self._app: Optional[Application] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Build the application and start polling (blocking call)."""
        if not self._token:
            logger.error("TELEGRAM_BOT_TOKEN is not set – bot cannot start.")
            return

        self._app = (
            Application.builder()
            .token(self._token)
            .build()
        )
        self._register_handlers()
        logger.info("Telegram bot starting…")
        self._app.run_polling(allowed_updates=Update.ALL_TYPES)

    def _register_handlers(self) -> None:
        assert self._app is not None
        app = self._app

        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("status", self._cmd_status))
        app.add_handler(CommandHandler("run", self._cmd_run))
        app.add_handler(CommandHandler("memory", self._cmd_memory))
        app.add_handler(CommandHandler("selfmod", self._cmd_selfmod))
        app.add_handler(CommandHandler("anon", self._cmd_anon))
        app.add_handler(CommandHandler("voice", self._cmd_voice))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

    # ── Access control ────────────────────────────────────────────────────────

    def _is_allowed(self, update: Update) -> bool:
        if not self._allowed_users:
            return True  # Public mode
        user = update.effective_user
        if user is None:
            return False
        return user.id in self._allowed_users

    async def _reject(self, update: Update) -> None:
        await update.message.reply_text(  # type: ignore[union-attr]
            "⛔ Access denied.  This is a private MirAI instance."
        )

    # ── Message handler ───────────────────────────────────────────────────────

    async def _handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._is_allowed(update):
            await self._reject(update)
            return

        text = update.message.text or ""  # type: ignore[union-attr]

        # Okabe Easter egg
        okabe_prefix = ""
        for trigger in self._okabe_triggers:
            if trigger.lower() in text.lower():
                okabe_prefix = f"_{random.choice(self._catchphrases)}_\n\n"
                break

        # Forward to agent
        await update.message.reply_chat_action("typing")  # type: ignore[union-attr]
        response = await asyncio.get_event_loop().run_in_executor(
            None, self._agent.chat, text
        )
        reply = okabe_prefix + response
        await update.message.reply_text(  # type: ignore[union-attr]
            reply[:4096],  # Telegram message limit
            parse_mode=ParseMode.MARKDOWN,
        )

    # ── Commands ──────────────────────────────────────────────────────────────

    async def _cmd_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._is_allowed(update):
            await self._reject(update)
            return
        name = settings.agent_name
        msg = (
            f"*{name} online.* El Psy Congroo.\n\n"
            "I am your autonomous AI assistant running on Kali Linux / WSL2.\n\n"
            "*Commands:*\n"
            "/status – System status\n"
            "/run `<cmd>` – Run a shell command\n"
            "/memory – Show conversation memory\n"
            "/selfmod `<instruction>` – Self-modify my code\n"
            "/anon – Rotate Tor identity\n"
            "/voice – Toggle voice mode\n\n"
            "Or just talk to me normally."
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)  # type: ignore[union-attr]

    async def _cmd_status(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._is_allowed(update):
            await self._reject(update)
            return
        from mirai.anonymity import get_current_ip
        ip = await asyncio.get_event_loop().run_in_executor(None, get_current_ip)
        mem_size = len(self._agent.memory)
        voice_status = "on" if self._agent.voice.is_enabled else "off"
        tor_status = "enabled" if settings.tor_enabled else "disabled"
        msg = (
            f"*{settings.agent_name} Status*\n"
            f"Exit IP: `{ip}`\n"
            f"Tor: {tor_status}\n"
            f"Memory messages: {mem_size}\n"
            f"Voice: {voice_status}\n"
            f"GitHub: {'connected' if self._agent.github.is_connected() else 'disconnected'}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)  # type: ignore[union-attr]

    async def _cmd_run(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._is_allowed(update):
            await self._reject(update)
            return
        cmd = " ".join(context.args or [])
        if not cmd:
            await update.message.reply_text("Usage: /run `<command>`", parse_mode=ParseMode.MARKDOWN)  # type: ignore[union-attr]
            return
        result = await asyncio.get_event_loop().run_in_executor(
            None, self._agent.kali.run, cmd
        )
        stdout = result["stdout"][:1500] or "(no output)"
        stderr = result["stderr"][:500] or ""
        rc = result["rc"]
        msg = f"*`{cmd}`* → rc={rc}\n```\n{stdout}"
        if stderr:
            msg += f"\n[stderr] {stderr}"
        msg += "\n```"
        await update.message.reply_text(msg[:4096], parse_mode=ParseMode.MARKDOWN)  # type: ignore[union-attr]

    async def _cmd_memory(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._is_allowed(update):
            await self._reject(update)
            return
        msgs = self._agent.memory.get_messages()[-10:]
        if not msgs:
            await update.message.reply_text("Memory is empty.")  # type: ignore[union-attr]
            return
        lines = [f"*{m['role']}:* {m['content'][:120]}" for m in msgs]
        await update.message.reply_text(  # type: ignore[union-attr]
            "\n\n".join(lines)[:4096], parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_selfmod(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._is_allowed(update):
            await self._reject(update)
            return
        instruction = " ".join(context.args or [])
        if not instruction:
            await update.message.reply_text(  # type: ignore[union-attr]
                "Usage: /selfmod `<natural-language instruction>`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        await update.message.reply_text("🔧 Self-modification in progress…")  # type: ignore[union-attr]
        result = await asyncio.get_event_loop().run_in_executor(
            None, self._agent.self_mod.add_feature, instruction
        )
        await update.message.reply_text(result[:4096], parse_mode=ParseMode.MARKDOWN)  # type: ignore[union-attr]

    async def _cmd_anon(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._is_allowed(update):
            await self._reject(update)
            return
        from mirai.anonymity import rotate_identity, get_current_ip
        await update.message.reply_text("🔄 Rotating Tor identity…")  # type: ignore[union-attr]
        ok = await asyncio.get_event_loop().run_in_executor(None, rotate_identity)
        ip = await asyncio.get_event_loop().run_in_executor(None, get_current_ip)
        status = "✅ Rotated" if ok else "⚠️ Rotation failed (is Tor running?)"
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{status}\nNew exit IP: `{ip}`", parse_mode=ParseMode.MARKDOWN
        )

    async def _cmd_voice(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._is_allowed(update):
            await self._reject(update)
            return
        await update.message.reply_text(  # type: ignore[union-attr]
            "Voice toggle requires restarting with VOICE_ENABLED=true/false in .env."
        )
