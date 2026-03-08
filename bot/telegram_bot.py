"""
Telegram Bot — MirAI_OS with Okabe Personality

Uses python-telegram-bot v20+ async API.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.personality.okabe import OKABE_SYSTEM_PROMPT, apply_personality
from core.llm_engine import LLMEngine
from core.context_optimizer import optimizer
from config.settings import settings


# Per-user conversation history (in-memory, bounded)
_HISTORY: dict[int, list[dict]] = {}
_MAX_HISTORY = 40


class MirAIBot:
    """Telegram bot wrapping the MirAI LLM engine with Okabe persona."""

    def __init__(self, token: Optional[str] = None) -> None:
        self.token = token or settings.telegram_bot_token
        self._engine: Optional[LLMEngine] = None
        self.app: Optional[Application] = None

    # ------------------------------------------------------------------
    # Bot commands
    # ------------------------------------------------------------------

    async def start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else 0
        _HISTORY.pop(user_id, None)
        await update.message.reply_text(
            "Fuhahaha! I am Hououin Kyouma! MirAI_OS is online. "
            "What experiment shall we run today, lab member? El Psy Kongroo."
        )

    async def help_cmd(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Commands:\n"
            "/start — Reset conversation\n"
            "/status — Hardware status\n"
            "/agent <task> — Run autonomous agent\n"
            "/lab — Open lab interface\n"
            "/clear — Clear history\n\n"
            "Or just send me any message!"
        )

    async def status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        snap = optimizer.get_snapshot()
        budget = optimizer.get_budget()
        msg = (
            f"🖥 *MirAI_OS Status*\n"
            f"Platform: `{snap.platform}`\n"
            f"RAM: `{snap.ram_available_gb:.1f}/{snap.ram_total_gb:.1f} GB` "
            f"({snap.ram_used_pct:.0f}% used)\n"
            f"GPU: `{snap.gpu_name}` ({snap.gpu_vram_mb} MB)\n"
            f"Legion Go: `{'✅' if snap.is_legion_go else '❌'}`\n\n"
            f"⚙️ *AI Budget*\n"
            f"Max tokens: `{budget.max_tokens}`\n"
            f"Batch size: `{budget.batch_size}`\n"
            f"GPU layers: `{budget.gpu_layers}`"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def clear(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else 0
        _HISTORY.pop(user_id, None)
        await update.message.reply_text("History cleared. A new world line begins!")

    async def agent_cmd(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        task = " ".join(ctx.args) if ctx.args else ""
        if not task:
            await update.message.reply_text("Usage: /agent <task description>")
            return
        await update.message.reply_text("⚙️ Agent activated… running task autonomously.")
        from core.agent_flow import AgentFlow  # noqa: PLC0415
        agent = AgentFlow()
        result = await agent.run(task)
        await update.message.reply_text(f"✅ Result:\n{result}")

    async def handle_message(
        self, update: Update, ctx: ContextTypes.DEFAULT_TYPE
    ) -> None:
        user_id = update.effective_user.id if update.effective_user else 0
        user_text = update.message.text or ""

        history = _HISTORY.setdefault(user_id, [])
        budget = optimizer.get_budget()

        # Trim history to budget
        while len(history) > min(_MAX_HISTORY, budget.max_history_turns * 2):
            history.pop(0)

        async with LLMEngine(system_prompt=OKABE_SYSTEM_PROMPT) as engine:
            reply = await engine.chat(user_text, history=history)

        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": reply})

        await update.message.reply_text(reply)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def build(self) -> Application:
        self.app = (
            Application.builder()
            .token(self.token)
            .build()
        )
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_cmd))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("clear", self.clear))
        self.app.add_handler(CommandHandler("agent", self.agent_cmd))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        return self.app

    def run(self) -> None:
        """Start the bot (blocking)."""
        app = self.build()
        app.run_polling()
