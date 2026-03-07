"""
MirAI_OS Telegram Bot
Provides remote AI access via Telegram.
"""

import logging
import threading
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot that forwards messages to the AI and replies with the response."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.token: str = self.config.get("telegram_token", "")
        self.allowed_user_ids = self.config.get("telegram_allowed_users", [])
        self._app: Any = None
        self._thread: Optional[threading.Thread] = None
        self._process_fn = None  # set by CoreOrchestrator

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if not self.token:
            logger.warning(
                "Telegram token not configured – bot disabled. "
                "Set 'telegram_token' in config.yaml."
            )
            return
        self._thread = threading.Thread(target=self._run_bot, daemon=True)
        self._thread.start()
        logger.info("TelegramBot started.")

    def stop(self) -> None:
        if self._app:
            try:
                self._app.stop_running()
            except Exception:
                pass
        logger.info("TelegramBot stopped.")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def set_process_function(self, fn) -> None:
        """Inject the AI processing function (called with user message, returns string)."""
        self._process_fn = fn

    def _run_bot(self) -> None:
        try:
            from telegram import Update  # type: ignore
            from telegram.ext import (  # type: ignore
                Application,
                CommandHandler,
                ContextTypes,
                MessageHandler,
                filters,
            )

            async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
                await update.message.reply_text(
                    "MirAI online. Send me a message to begin. El Psy Kongroo."
                )

            async def handle_message(
                update: Update, ctx: ContextTypes.DEFAULT_TYPE
            ) -> None:
                user_id = update.effective_user.id
                if self.allowed_user_ids and user_id not in self.allowed_user_ids:
                    await update.message.reply_text("Unauthorised.")
                    return
                text = update.message.text or ""
                if self._process_fn:
                    reply = self._process_fn(text)
                else:
                    reply = "[AI not connected]"
                await update.message.reply_text(reply)

            self._app = Application.builder().token(self.token).build()
            self._app.add_handler(CommandHandler("start", start_cmd))
            self._app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
            )
            self._app.run_polling()
        except ImportError:
            logger.warning(
                "python-telegram-bot not installed. "
                "Install: pip install python-telegram-bot"
            )
        except Exception as exc:
            logger.error("TelegramBot error: %s", exc)
