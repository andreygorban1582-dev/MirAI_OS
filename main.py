"""
MirAI_OS  –  Main application entry point
Runs locally (outside Docker) or inside the orchestrator container.
CLI / Telegram / Voice modes.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
)
logger = logging.getLogger("mirai")

# ─── Service URLs (from env or defaults) ──────────────────────────────────────
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8080")
WHISPER_URL      = os.getenv("WHISPER_URL",      "http://localhost:8400")
CSM_URL          = os.getenv("CSM_URL",           "http://localhost:8300")
OLLAMA_URL       = os.getenv("OLLAMA_URL",        "http://localhost:11434")
OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL",      "nous-hermes-2-mistral-7b-dpo")
TG_TOKEN         = os.getenv("TELEGRAM_BOT_TOKEN", "")


# ═══════════════════════════════════════════════════════════════════════════════
# LLM Client  (direct Ollama – used when not running inside Docker stack)
# ═══════════════════════════════════════════════════════════════════════════════

class LLMClient:
    """Ollama-first, OpenRouter fallback."""

    def __init__(self) -> None:
        import httpx
        self._http = httpx.AsyncClient(timeout=120)
        self._or_key = os.getenv("OPENROUTER_API_KEY", "")

    async def chat(self, messages: list[dict], model: str | None = None) -> str:
        m = model or OLLAMA_MODEL
        try:
            return await self._ollama(messages, m)
        except Exception as exc:
            logger.warning("[LLM] Ollama failed (%s)", exc)
            if self._or_key:
                return await self._openrouter(messages, m)
            raise

    async def _ollama(self, messages: list[dict], model: str) -> str:
        r = await self._http.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
        )
        r.raise_for_status()
        return r.json()["message"]["content"]

    async def _openrouter(self, messages: list[dict], model: str) -> str:
        r = await self._http.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {self._or_key}"},
            json={"model": model, "messages": messages},
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    async def close(self) -> None:
        await self._http.aclose()


# ═══════════════════════════════════════════════════════════════════════════════
# Mod loader (Mod 2 – hot reload + on_startup / on_shutdown)
# ═══════════════════════════════════════════════════════════════════════════════

import importlib
import importlib.util
import types
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class Mod:
    name: str
    version: str
    module: types.ModuleType

    async def setup(self, bot: Any, llm: Any, ctx: dict) -> None:
        if hasattr(self.module, "setup"):
            try:
                result = self.module.setup(bot, llm, ctx)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.error("[mod:%s] setup: %s", self.name, exc)

    async def on_message(self, message: str, ctx: dict) -> Optional[str]:
        if hasattr(self.module, "on_message"):
            try:
                r = self.module.on_message(message, ctx)
                return await r if asyncio.iscoroutine(r) else r
            except Exception as exc:
                logger.error("[mod:%s] on_message: %s", self.name, exc)
        return None

    async def on_startup(self, ctx: dict) -> None:  # Mod 2
        if hasattr(self.module, "on_startup"):
            try:
                r = self.module.on_startup(ctx)
                if asyncio.iscoroutine(r):
                    await r
            except Exception as exc:
                logger.error("[mod:%s] on_startup: %s", self.name, exc)

    async def on_shutdown(self, ctx: dict) -> None:  # Mod 2
        if hasattr(self.module, "on_shutdown"):
            try:
                r = self.module.on_shutdown(ctx)
                if asyncio.iscoroutine(r):
                    await r
            except Exception as exc:
                logger.error("[mod:%s] on_shutdown: %s", self.name, exc)


class ModLoader:
    def __init__(self) -> None:
        self._mods: dict[str, Mod] = {}

    def load_file(self, path: str | Path) -> Optional[Mod]:
        path = Path(path)
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if not spec or not spec.loader:
            return None
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore
        except Exception as exc:
            logger.error("[ModLoader] load %s: %s", path, exc)
            return None
        mod = Mod(
            name=getattr(module, "MOD_NAME", path.stem),
            version=getattr(module, "MOD_VERSION", "0.0.0"),
            module=module,
        )
        self._mods[mod.name] = mod
        logger.info("[ModLoader] %s v%s", mod.name, mod.version)
        return mod

    def load_directory(self, directory: str | Path) -> list[Mod]:
        return [
            mod
            for p in sorted(Path(directory).glob("*.py"))
            if (mod := self.load_file(p))
        ]

    def reload(self, name: str) -> bool:  # Mod 2
        if mod := self._mods.get(name):
            try:
                importlib.reload(mod.module)
                return True
            except Exception as exc:
                logger.error("[ModLoader] reload %s: %s", name, exc)
        return False

    @property
    def mods(self) -> list[Mod]:
        return list(self._mods.values())

    async def dispatch(self, message: str, ctx: dict) -> Optional[str]:
        for mod in self.mods:
            r = await mod.on_message(message, ctx)
            if r is not None:
                return r
        return None

    async def startup_all(self, ctx: dict) -> None:
        for mod in self.mods:
            await mod.on_startup(ctx)

    async def shutdown_all(self, ctx: dict) -> None:
        for mod in self.mods:
            await mod.on_shutdown(ctx)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI mode
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = (
    "You are MirAI, an advanced AI operating system assistant running on "
    "a Legion Go handheld gaming PC under Kali Linux / WSL2. "
    "You coordinate containers, tools, and agents to help the user accomplish any task."
)


async def run_cli(llm: LLMClient, loader: ModLoader) -> None:
    history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    ctx: dict = {"mode": "cli"}
    await loader.startup_all(ctx)

    print("\n┌──────────────────────────────────────────────────────┐")
    print("│  MirAI_OS  –  CLI mode  (type 'exit' to quit)        │")
    print("└──────────────────────────────────────────────────────┘\n")

    try:
        while True:
            try:
                user_input = input("You ▶ ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "q"}:
                break

            # Mod intercept
            mod_reply = await loader.dispatch(user_input, ctx)
            if mod_reply is not None:
                print(f"\nMirAI ▶ {mod_reply}\n")
                continue

            history.append({"role": "user", "content": user_input})
            try:
                reply = await llm.chat(history)
            except Exception as exc:
                reply = f"[Error] {exc}"

            history.append({"role": "assistant", "content": reply})
            print(f"\nMirAI ▶ {reply}\n")

            # Keep rolling context at 40 messages
            if len(history) > 42:
                history = [history[0]] + history[-40:]
    finally:
        await loader.shutdown_all(ctx)
        await llm.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Telegram mode
# ═══════════════════════════════════════════════════════════════════════════════

async def run_telegram(llm: LLMClient, loader: ModLoader) -> None:
    if not TG_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)

    from telegram import Update
    from telegram.ext import Application, MessageHandler, filters, ContextTypes

    sessions: dict[int, list[dict]] = {}

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id if update.effective_chat else 0
        text = update.message.text or "" if update.message else ""

        if chat_id not in sessions:
            sessions[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        history = sessions[chat_id]

        mod_reply = await loader.dispatch(text, {"mode": "telegram", "chat_id": chat_id})
        if mod_reply:
            await update.message.reply_text(mod_reply)
            return

        history.append({"role": "user", "content": text})
        try:
            reply = await llm.chat(history)
        except Exception as exc:
            reply = f"Error: {exc}"

        history.append({"role": "assistant", "content": reply})
        if len(history) > 42:
            sessions[chat_id] = [history[0]] + history[-40:]

        await update.message.reply_text(reply)

    ctx: dict = {"mode": "telegram"}
    await loader.startup_all(ctx)

    app = (
        Application.builder()
        .token(TG_TOKEN)
        .build()
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("[Telegram] Bot running…")
    await app.run_polling()


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="MirAI_OS")
    parser.add_argument(
        "--mode", choices=["cli", "telegram"], default="cli",
        help="Run mode (default: cli)",
    )
    parser.add_argument(
        "--mods-dir", default="mods",
        help="Directory to load mods from",
    )
    args = parser.parse_args()

    llm    = LLMClient()
    loader = ModLoader()

    mods_path = Path(args.mods_dir)
    if mods_path.exists():
        loader.load_directory(mods_path)

    if args.mode == "cli":
        asyncio.run(run_cli(llm, loader))
    elif args.mode == "telegram":
        asyncio.run(run_telegram(llm, loader))


if __name__ == "__main__":
    main()
