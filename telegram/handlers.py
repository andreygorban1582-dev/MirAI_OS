"""
MirAI OS — Telegram Message Handlers
Processes text, voice messages, commands, and media.
"""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

from telegram import Update, Voice
from telegram.ext import ContextTypes

from core.config import cfg
from telegram.ui import (
    THINKING_BANNER, agent_update, command_output, error_panel,
    task_complete, task_started, welcome_message,
)

logger = logging.getLogger("mirai.telegram.handlers")


def is_admin(user_id: int) -> bool:
    admins = cfg.telegram_admin_ids
    return not admins or user_id in admins


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Access denied. The Organization has been notified.")
        return
    name = update.effective_user.first_name or "Lab Member"
    await update.message.reply_text(welcome_message(name), parse_mode="Markdown")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    help_text = """```
╔══ FUTURE GADGET LAB — COMMAND MANUAL ════════╗
║  /start        Boot sequence + welcome        ║
║  /help         This manual                    ║
║  /status       System status panel            ║
║  /keys         OpenRouter key pool status     ║
║  /nodes        Compute node grid              ║
║  /kali <cmd>   Run a Kali Linux command       ║
║  /scan <host>  Quick nmap scan                ║
║  /web <url>    Browse a URL                   ║
║  /code <py>    Execute Python code            ║
║  /bash <cmd>   Execute Bash command           ║
║  /push         Commit & push to GitHub        ║
║  /addkey       Add an API key                 ║
║  /addnode      Add a compute node             ║
║  /inject       Inject new capability code     ║
║  /memory       Show memory stats              ║
╚═══════════════════════════════════════════════╝
  Or just TALK — I understand natural language.
  Voice messages are supported. El Psy Kongroo.
```"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    from core.llm import llm
    from core.memory import memory
    keys = llm.key_status()
    rows = [
        ("Core LLM", cfg.llm.get("primary_model", "?")[:28]),
        ("API Keys", f"{len([k for k in keys if k['requests'] > 0])}/{len(keys)} active"),
        ("Memory Tier 1", "Redis (short-term)"),
        ("Memory Tier 2", "SQLite (summaries)"),
        ("Memory Tier 3", "ChromaDB (vectors)"),
        ("Active Nodes", str(len(cfg.active_nodes()))),
        ("Kali Tools", "Full arsenal online"),
        ("Voice", "Whisper STT + Sesame TTS"),
        ("Self-Modify", "GitHub sync enabled"),
    ]
    from telegram.ui import status_panel
    panel = status_panel("MIRAI OS STATUS", rows)
    await update.message.reply_text(panel, parse_mode="Markdown")


async def cmd_keys(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    from core.llm import llm
    from telegram.ui import llm_key_status
    await update.message.reply_text(llm_key_status(llm.key_status()), parse_mode="Markdown")


async def cmd_nodes(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    from telegram.ui import node_grid
    await update.message.reply_text(node_grid(cfg.nodes), parse_mode="Markdown")


async def cmd_kali(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    raw = " ".join(ctx.args) if ctx.args else ""
    if not raw:
        await update.message.reply_text("`Usage: /kali <command>`", parse_mode="Markdown")
        return
    await update.message.reply_text(task_started(raw), parse_mode="Markdown")
    from tools.kali_tools import kali
    t = time.monotonic()
    result = await kali.run_raw(raw)
    dur = time.monotonic() - t
    output = command_output(raw, result.output or result.stderr, result.success)
    await update.message.reply_text(output, parse_mode="Markdown")
    await update.message.reply_text(task_complete(raw, dur), parse_mode="Markdown")


async def cmd_scan(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    target = " ".join(ctx.args) if ctx.args else ""
    if not target:
        await update.message.reply_text("`Usage: /scan <host/IP>`", parse_mode="Markdown")
        return
    await update.message.reply_text(
        f"`[⚡ INITIATING SCAN]` Target: `{target}`\nThe Organization's defenses will crumble...",
        parse_mode="Markdown",
    )
    from tools.kali_tools import kali
    result = await kali.run("nmap", f"-sV --top-ports 1000 {target}", timeout=180)
    output = command_output(f"nmap {target}", result.output or result.stderr, result.success)
    await update.message.reply_text(output, parse_mode="Markdown")


async def cmd_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    code = " ".join(ctx.args) if ctx.args else ""
    if not code:
        await update.message.reply_text("`Usage: /code <python code>`", parse_mode="Markdown")
        return
    from agents.code_agent import CodeAgent
    from agents.base_agent import AgentTask
    import uuid
    agent = CodeAgent()
    task = AgentTask(task_id=str(uuid.uuid4()), description=code, params={"action": "run_python", "code": code})
    result = await agent.execute(task)
    output = command_output(f"python: {code[:40]}...", result.output or result.error or "", result.success)
    await update.message.reply_text(output, parse_mode="Markdown")


async def cmd_bash(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    cmd = " ".join(ctx.args) if ctx.args else ""
    if not cmd:
        await update.message.reply_text("`Usage: /bash <command>`", parse_mode="Markdown")
        return
    from tools.kali_tools import kali
    result = await kali.run_raw(cmd)
    output = command_output(cmd, result.output or result.stderr, result.success)
    await update.message.reply_text(output, parse_mode="Markdown")


async def cmd_push(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    msg = " ".join(ctx.args) if ctx.args else "MirAI OS self-update"
    from agents.self_modify_agent import SelfModifyAgent
    from agents.base_agent import AgentTask
    import uuid
    agent = SelfModifyAgent()
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        description="commit_and_push",
        params={"action": "commit_and_push", "message": msg},
    )
    await update.message.reply_text("`[⚡ COMMITTING TO GITHUB...]`", parse_mode="Markdown")
    result = await agent.execute(task)
    output = command_output("git commit + push", result.output or result.error or "", result.success)
    await update.message.reply_text(output, parse_mode="Markdown")


async def cmd_memory(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    session_id = str(update.effective_user.id)
    from core.memory import memory
    short_count = memory.short.count(session_id)
    summaries = memory.medium.get_summaries(session_id, limit=10)
    from telegram.ui import status_panel
    rows = [
        ("Short-term msgs", str(short_count)),
        ("Summaries", str(len(summaries))),
        ("Vector store", "active"),
    ]
    await update.message.reply_text(status_panel("MEMORY STATUS", rows), parse_mode="Markdown")


# ── Main message handler (natural language) ───────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    user_text = update.message.text or ""
    session_id = str(update.effective_user.id)

    # Show typing indicator
    await update.message.chat.send_action("typing")

    # Get the orchestrator (imported here to avoid circular imports)
    from core.orchestrator import orchestrator
    try:
        response = await orchestrator.process(
            user_input=user_text,
            session_id=session_id,
        )
        # Send in chunks if too long
        for chunk in _split_message(response):
            await update.message.reply_text(chunk, parse_mode="Markdown")
    except Exception as e:
        logger.exception("Message handling error")
        await update.message.reply_text(
            error_panel(str(e), "handle_message"),
            parse_mode="Markdown",
        )


async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Process voice messages: download → STT → orchestrate → TTS → reply."""
    if not is_admin(update.effective_user.id):
        return
    session_id = str(update.effective_user.id)

    await update.message.reply_text("`[⚡ VOICE CHANNEL]` Receiving transmission...", parse_mode="Markdown")
    await update.message.chat.send_action("typing")

    try:
        # Download voice file
        voice: Voice = update.message.voice
        file = await ctx.bot.get_file(voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            voice_path = tmp.name

        # STT
        from voice.stt import transcribe
        transcript = await transcribe(voice_path)
        Path(voice_path).unlink(missing_ok=True)

        if not transcript.strip():
            await update.message.reply_text("`[STT]` Could not decode transmission.", parse_mode="Markdown")
            return

        await update.message.reply_text(
            f"`[STT DECODED]` _{transcript}_",
            parse_mode="Markdown",
        )

        # Orchestrate
        from core.orchestrator import orchestrator
        response_text = await orchestrator.process(user_input=transcript, session_id=session_id)

        # TTS
        from voice.tts import synthesize
        audio_path = await synthesize(response_text)

        if audio_path and Path(audio_path).exists():
            with open(audio_path, "rb") as af:
                await update.message.reply_voice(voice=af)
            Path(audio_path).unlink(missing_ok=True)
        else:
            # Fallback to text
            for chunk in _split_message(response_text):
                await update.message.reply_text(chunk, parse_mode="Markdown")

    except Exception as e:
        logger.exception("Voice handling error")
        await update.message.reply_text(error_panel(str(e), "handle_voice"), parse_mode="Markdown")


# ── Utility ───────────────────────────────────────────────────────────────────

def _split_message(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
    return chunks
