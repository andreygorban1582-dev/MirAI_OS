"""
MirAI_OS – main.py
Command-line entry point for the MirAI application.
Supports --mode cli|telegram and --help.

This script can also be run directly (without Docker) for local development;
it will connect to a locally running Ollama instance.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "dolphin-mistral")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

DEFAULT_SYSTEM = (
    "You are Okabe Rintaro, a mad scientist AI assistant known as MirAI. "
    "You are helpful, brilliant, and slightly dramatic."
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("mirai.main")

# ─────────────────────────────────────────────────────────────────────────────
# LLM Client
# ─────────────────────────────────────────────────────────────────────────────


class LLMClient:
    """Ollama primary, OpenRouter fallback."""

    def __init__(self, model: str = OLLAMA_MODEL) -> None:
        self._http = httpx.AsyncClient(timeout=120.0)
        self.model = model

    async def chat(
        self,
        prompt: str,
        system: str = DEFAULT_SYSTEM,
        history: Optional[list] = None,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        for msg in (history or []):
            messages.append(msg)
        messages.append({"role": "user", "content": prompt})

        try:
            return await self._ollama_chat(messages)
        except Exception as exc:
            log.warning("Ollama unavailable (%s); trying OpenRouter…", exc)

        if OPENROUTER_API_KEY:
            try:
                return await self._openrouter_chat(messages)
            except Exception as exc2:
                log.error("OpenRouter also failed: %s", exc2)

        raise RuntimeError(
            "All LLM backends failed. "
            "Is Ollama running? Set OPENROUTER_API_KEY as fallback."
        )

    async def _ollama_chat(self, messages: list) -> str:
        url = f"{OLLAMA_HOST}/api/chat"
        payload = {"model": self.model, "messages": messages, "stream": False}
        resp = await self._http.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    async def _openrouter_chat(self, messages: list) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
        payload = {
            "model": "nousresearch/nous-hermes-2-mistral-7b-dpo",
            "messages": messages,
        }
        resp = await self._http.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def is_available(self) -> bool:
        try:
            resp = await self._http.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._http.aclose()


# ─────────────────────────────────────────────────────────────────────────────
# CLI Mode
# ─────────────────────────────────────────────────────────────────────────────


async def run_cli(llm: LLMClient) -> None:
    print("\nMirAI_OS – Interactive CLI")
    print("Type 'exit' or Ctrl+C to quit.\n")

    available = await llm.is_available()
    if not available:
        print(f"[WARN] Ollama not reachable at {OLLAMA_HOST}.")
        if not OPENROUTER_API_KEY:
            print("[WARN] No OPENROUTER_API_KEY set. Responses may fail.")
        else:
            print("[INFO] Will use OpenRouter as fallback.")
    else:
        print(f"[INFO] Connected to Ollama ({llm.model}) at {OLLAMA_HOST}\n")

    history: list = []

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("El Psy Kongroo.")
                break

            if user_input.lower() == "/clear":
                history.clear()
                print("[History cleared]")
                continue

            try:
                reply = await llm.chat(user_input, history=history)
            except Exception as exc:
                print(f"[ERROR] {exc}")
                continue

            print(f"MirAI: {reply}\n")

            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": reply})
            # Keep last 40 turns
            if len(history) > 80:
                history = history[-80:]

    except KeyboardInterrupt:
        print("\nEl Psy Kongroo.")


# ─────────────────────────────────────────────────────────────────────────────
# Telegram Mode
# ─────────────────────────────────────────────────────────────────────────────


async def run_telegram(llm: LLMClient) -> None:
    if not TELEGRAM_TOKEN:
        log.error("TELEGRAM_TOKEN is not set. Cannot start Telegram mode.")
        sys.exit(1)

    try:
        from telegram import Update
        from telegram.ext import (
            Application,
            CommandHandler,
            MessageHandler,
            filters,
            ContextTypes,
        )
    except ImportError:
        log.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
        sys.exit(1)

    # Per-chat history stored in memory (use Redis for persistence in Docker)
    chat_history: dict[int, list] = {}

    async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Hahaha! I am Okabe Rintaro – MirAI, the mad scientist AI. "
            "Ask me anything, Lab Member!"
        )

    async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        chat_history.pop(chat_id, None)
        await update.message.reply_text("History cleared. A fresh start!")

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        user_text = update.message.text or ""
        if not user_text.strip():
            return

        await update.message.chat.send_action("typing")
        history = chat_history.get(chat_id, [])

        try:
            reply = await llm.chat(user_text, history=history)
        except Exception as exc:
            reply = f"El Psy Kongroo… an error occurred: {exc}"

        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": reply})
        if len(history) > 80:
            history = history[-80:]
        chat_history[chat_id] = history

        await update.message.reply_text(reply)

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Starting Telegram bot…")
    await app.run_polling()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mirai",
        description="MirAI_OS – AI Operating System CLI",
    )
    parser.add_argument(
        "--mode",
        choices=["cli", "telegram"],
        default="cli",
        help="Run mode: 'cli' for interactive shell, 'telegram' for bot (default: cli)",
    )
    parser.add_argument(
        "--model",
        default=OLLAMA_MODEL,
        help=f"Ollama model to use (default: {OLLAMA_MODEL})",
    )
    return parser.parse_args()


async def _main() -> None:
    args = parse_args()

    llm = LLMClient(model=args.model)
    try:
        if args.mode == "telegram":
            await run_telegram(llm)
        else:
            await run_cli(llm)
    finally:
        await llm.close()


def main() -> None:
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
