"""
MirAI OS — Telegram Bot Entry Point
Registers all handlers and starts the bot.
"""
from __future__ import annotations

import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from core.config import cfg
from telegram.handlers import (
    cmd_bash,
    cmd_code,
    cmd_help,
    cmd_kali,
    cmd_keys,
    cmd_memory,
    cmd_nodes,
    cmd_push,
    cmd_scan,
    cmd_start,
    cmd_status,
    handle_message,
    handle_voice,
)

logger = logging.getLogger("mirai.telegram.bot")


def build_app() -> Application:
    token = cfg.telegram_token
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured in .env!")

    app = (
        Application.builder()
        .token(token)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("keys", cmd_keys))
    app.add_handler(CommandHandler("nodes", cmd_nodes))
    app.add_handler(CommandHandler("kali", cmd_kali))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("code", cmd_code))
    app.add_handler(CommandHandler("bash", cmd_bash))
    app.add_handler(CommandHandler("push", cmd_push))
    app.add_handler(CommandHandler("memory", cmd_memory))

    # Voice messages
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Text messages (natural language — must be last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Telegram bot handlers registered.")
    return app


async def run_bot() -> None:
    app = build_app()
    logger.info("Starting MirAI Telegram bot... El Psy Kongroo.")
    await app.run_polling(drop_pending_updates=True)
