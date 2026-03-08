"""
MirAI_OS – Main Orchestrator
============================
Features:
  • Local 8B uncensored LLM (dolphin-llama3:8b via Ollama)
  • 303-character 24/7 game engine
  • WSL/Linux environment control via chat commands
  • Credential prompting in chat
  • Kali Linux tools integration
  • Telegram bot + CLI modes

Usage:
  python main.py              # interactive CLI
  python main.py --telegram   # Telegram bot mode
"""
from __future__ import annotations

import asyncio
import getpass
import json
import logging
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Optional dependencies ──────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import httpx
    _HTTPX_OK = True
except ImportError:
    _HTTPX_OK = False

try:
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        ContextTypes,
        filters,
    )
    _TG_OK = True
except ImportError:
    _TG_OK = False

from game_engine import GameEngine

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mirai.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("MirAI_OS")

# ── Configuration ──────────────────────────────────────────────────────────
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "dolphin-llama3:8b")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_ID: str = os.getenv("TELEGRAM_ADMIN_ID", "")
WSL_ENABLED: bool = os.getenv("WSL_ENABLED", "true").lower() == "true"
KALI_ENABLED: bool = os.getenv("KALI_ENABLED", "false").lower() == "true"
CREDENTIALS_FILE = Path(".credentials.json")


# ═══════════════════════════════════════════════════════════════════════════ #
# LLM Client                                                                  #
# ═══════════════════════════════════════════════════════════════════════════ #

class LLMClient:
    """Priority: Ollama (local 8B uncensored) → OpenRouter fallback."""

    SYSTEM_PROMPT = (
        "You are MirAI, an advanced AI assistant that runs as an operating system. "
        "You can control the local Linux/WSL environment, manage a 24/7 RPG game with "
        "303 characters, and help with Kali Linux security tools. "
        "When you need to execute a shell command, wrap it exactly like: "
        "<SHELL>command here</SHELL>. "
        "When you need credentials from the user, respond with: "
        "<ASK_CRED>label:description</ASK_CRED> (e.g. <ASK_CRED>API_KEY:Your OpenRouter API key</ASK_CRED>). "
        "You speak directly and helpfully. El Psy Kongroo."
    )

    def __init__(self) -> None:
        self._session: Optional[Any] = None

    async def _ollama_chat(self, messages: List[dict]) -> str:
        if not _HTTPX_OK:
            return "[Error: httpx not installed. Run: pip install httpx]"
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
            }
            try:
                resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
                resp.raise_for_status()
                return resp.json()["message"]["content"]
            except httpx.ConnectError:
                return None   # signal fallback
            except Exception as exc:
                logger.warning("Ollama error: %s", exc)
                return None

    async def _openrouter_chat(self, messages: List[dict]) -> str:
        if not _HTTPX_OK or not OPENROUTER_API_KEY:
            return "[No LLM available. Start Ollama: ollama serve]"
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "nousresearch/nous-hermes-2-mistral-7b-dpo",
                "messages": messages,
            }
            try:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except Exception as exc:
                return f"[LLM Error: {exc}]"

    async def chat(
        self, user_message: str, history: Optional[List[dict]] = None
    ) -> str:
        history = history or []
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        messages.extend(history[-10:])   # keep last 10 turns for context
        messages.append({"role": "user", "content": user_message})

        result = await self._ollama_chat(messages)
        if result is None:
            logger.info("Ollama unavailable, falling back to OpenRouter.")
            result = await self._openrouter_chat(messages)
        return result


# ═══════════════════════════════════════════════════════════════════════════ #
# WSL / Shell Controller                                                      #
# ═══════════════════════════════════════════════════════════════════════════ #

# Commands that are never executed for safety
_BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"mkfs\.",
    r"dd\s+if=",
    r">\s*/dev/sd",
    r"chmod\s+-R\s+777\s+/",
    r":\(\)\{",          # fork bomb pattern: :(){
]
_BLOCKED_RE = [re.compile(p) for p in _BLOCKED_PATTERNS]

MAX_OUTPUT_CHARS = 4000


def _is_blocked(cmd: str) -> bool:
    for pattern in _BLOCKED_RE:
        if pattern.search(cmd):
            return True
    return False


async def run_shell_command(cmd: str, timeout: int = 30) -> str:
    """Execute a shell command in WSL/Linux and return output."""
    if not WSL_ENABLED:
        return "[WSL control disabled. Set WSL_ENABLED=true in .env]"
    if _is_blocked(cmd):
        return f"[BLOCKED: Potentially destructive command refused: {cmd!r}]"

    logger.info("Executing shell command: %s", cmd)
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            limit=1024 * 1024,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return f"[TIMEOUT after {timeout}s]"
        output = stdout.decode(errors="replace")
        if len(output) > MAX_OUTPUT_CHARS:
            output = output[:MAX_OUTPUT_CHARS] + "\n... [truncated]"
        return output or "(no output)"
    except Exception as exc:
        return f"[Shell Error: {exc}]"


# ═══════════════════════════════════════════════════════════════════════════ #
# Credential Manager                                                          #
# ═══════════════════════════════════════════════════════════════════════════ #

class CredentialManager:
    """Store/retrieve credentials securely in a local JSON file (chmod 600)."""

    def __init__(self) -> None:
        self._creds: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if CREDENTIALS_FILE.exists():
            try:
                self._creds = json.loads(CREDENTIALS_FILE.read_text())
            except Exception:
                self._creds = {}

    def _save(self) -> None:
        CREDENTIALS_FILE.write_text(json.dumps(self._creds, indent=2))
        try:
            CREDENTIALS_FILE.chmod(0o600)
        except Exception:
            pass

    def get(self, key: str) -> Optional[str]:
        # Check env first, then stored creds
        return os.getenv(key) or self._creds.get(key)

    def set(self, key: str, value: str) -> None:
        self._creds[key] = value
        self._save()
        # Also update the current process environment
        os.environ[key] = value

    def list_keys(self) -> List[str]:
        keys = set(self._creds.keys())
        # Add known env keys that are set
        for k in ["TELEGRAM_BOT_TOKEN", "OPENROUTER_API_KEY", "OLLAMA_MODEL"]:
            if os.getenv(k):
                keys.add(k)
        return sorted(keys)


# ═══════════════════════════════════════════════════════════════════════════ #
# Orchestrator                                                                #
# ═══════════════════════════════════════════════════════════════════════════ #

class MirAI_Orchestrator:
    """Central orchestrator connecting LLM, game engine, and WSL control."""

    def __init__(self) -> None:
        self.llm = LLMClient()
        self.game = GameEngine()
        self.creds = CredentialManager()
        self.histories: Dict[str, List[dict]] = {}   # per-user/chat history
        self._pending_creds: Dict[str, str] = {}     # label → description awaiting input

    # ── Response processing ────────────────────────────────────────────── #

    async def _handle_shell_tags(self, text: str) -> str:
        """Find all <SHELL>…</SHELL> blocks, execute them, replace with output."""
        pattern = re.compile(r"<SHELL>(.*?)</SHELL>", re.DOTALL)
        matches = pattern.findall(text)
        for cmd in matches:
            cmd = cmd.strip()
            output = await run_shell_command(cmd)
            text = text.replace(f"<SHELL>{cmd}</SHELL>", f"\n```\n$ {cmd}\n{output}\n```", 1)
        return text

    def _extract_cred_requests(self, text: str) -> List[Tuple[str, str]]:
        """Return list of (label, description) credential requests."""
        pattern = re.compile(r"<ASK_CRED>(.*?)</ASK_CRED>")
        results = []
        for match in pattern.findall(text):
            if ":" in match:
                label, desc = match.split(":", 1)
                results.append((label.strip(), desc.strip()))
        return results

    def _clean_tags(self, text: str) -> str:
        text = re.sub(r"<ASK_CRED>.*?</ASK_CRED>", "", text)
        return text.strip()

    # ── Game commands ──────────────────────────────────────────────────── #

    def _handle_game_command(self, text: str) -> Optional[str]:
        t = text.strip().lower()
        if t in ("/leaderboard", "leaderboard", "lb"):
            lb = self.game.leaderboard(20)
            lines = ["🏆 **Leaderboard** (Top 20)\n"]
            for entry in lb:
                status = "✅" if entry["alive"] else "💀"
                lines.append(
                    f"{entry['rank']}. {status} **{entry['name']}** "
                    f"({entry['universe']}) "
                    f"Lv{entry['level']} | W:{entry['wins']} L:{entry['losses']} "
                    f"⚡{entry['power']} 💰{entry['gold']}"
                )
            return "\n".join(lines)

        if t.startswith("/char ") or t.startswith("char "):
            name = text.split(" ", 1)[1].strip()
            info = self.game.character_info(name)
            if info:
                return (
                    f"**{info['name']}** ({info['universe']}) – {info['role']}\n"
                    f"Level {info['level']} | Power: {info['power_score']}\n"
                    f"HP:{info['hp']} ATK:{info['attack']} DEF:{info['defense']} "
                    f"SPD:{info['speed']} INT:{info['intelligence']}\n"
                    f"Wins: {info['wins']} | Losses: {info['losses']} | Gold: {info['gold']}\n"
                    f"Status: {'Alive ✅' if info['alive'] else 'Knocked Out 💀'}\n"
                    f"Abilities: {', '.join(info['abilities'])}"
                )
            return f"Character '{name}' not found. Try /leaderboard to see active characters."

        if t in ("/gamestatus", "gamestatus", "game status"):
            alive = sum(1 for c in self.game.characters if c.alive)
            return (
                f"🎮 **Game Status**\n"
                f"Round: {self.game.round}\n"
                f"Characters: {len(self.game.characters)} total, {alive} alive\n"
                f"Running: {'Yes ✅' if self.game.running else 'No ❌'}"
            )

        if t in ("/lastbattle", "last battle", "lastbattle"):
            if self.game.battle_log:
                return "```\n" + self.game.battle_log[-1] + "\n```"
            return "No battles recorded yet."

        return None

    # ── Credential commands ────────────────────────────────────────────── #

    def _handle_cred_command(self, text: str) -> Optional[str]:
        t = text.strip().lower()
        if t in ("/creds", "creds", "/credentials", "credentials"):
            keys = self.creds.list_keys()
            if not keys:
                return "No credentials stored yet."
            return "🔑 **Stored credential keys:**\n" + "\n".join(f"  • {k}" for k in keys)

        m = re.match(r"(?:/set_cred|set_cred)\s+(\w+)\s+(.+)", text.strip(), re.IGNORECASE)
        if m:
            key, value = m.group(1), m.group(2).strip()
            self.creds.set(key, value)
            return f"✅ Credential `{key}` saved."

        return None

    # ── Main process message ──────────────────────────────────────────── #

    async def process_message(
        self,
        user_id: str,
        text: str,
        *,
        provide_cred: Optional[Tuple[str, str]] = None,
    ) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Process a user message.

        Returns:
            (response_text, pending_cred_requests)

        pending_cred_requests is a list of (label, description) tuples that
        the caller should collect from the user and feed back via provide_cred.
        """
        # Handle credential provision
        if provide_cred:
            label, value = provide_cred
            self.creds.set(label, value)
            return f"✅ `{label}` has been saved securely.", []

        # Built-in commands
        game_resp = self._handle_game_command(text)
        if game_resp:
            return game_resp, []

        cred_resp = self._handle_cred_command(text)
        if cred_resp:
            return cred_resp, []

        if text.strip().lower() in ("/help", "help"):
            return HELP_TEXT, []

        # LLM response
        history = self.histories.setdefault(user_id, [])
        raw = await self.llm.chat(text, history)

        # Process shell commands embedded in response
        processed = await self._handle_shell_tags(raw)

        # Extract credential requests
        cred_requests = self._extract_cred_requests(processed)
        final = self._clean_tags(processed)

        # Update history
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": final})
        if len(history) > 20:
            history[:] = history[-20:]

        return final, cred_requests


HELP_TEXT = """
🤖 **MirAI_OS Commands**

**Game:**
  /leaderboard        – Top 20 characters by wins
  /char <name>        – Character stats & info
  /gamestatus         – Game engine status
  /lastbattle         – Last combat log

**WSL / Shell:**
  Just ask me to run any command, e.g.:
  "install nmap", "show disk usage", "list running services"

**Credentials:**
  /creds              – List stored credential keys
  /set_cred KEY value – Store a credential

**Other:**
  /help               – Show this message

Ask me anything! I can control your WSL environment, run Kali tools,
or just chat. El Psy Kongroo. 🧪
""".strip()


# ═══════════════════════════════════════════════════════════════════════════ #
# Telegram Bot Mode                                                           #
# ═══════════════════════════════════════════════════════════════════════════ #

def build_telegram_app(orchestrator: MirAI_Orchestrator, bot_token: Optional[str] = None) -> Any:
    if not _TG_OK:
        raise RuntimeError("python-telegram-bot not installed.")
    token = bot_token or TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set.")

    # Track pending credential requests per chat
    pending: Dict[int, Tuple[str, str]] = {}   # chat_id → (label, description)

    app = Application.builder().token(token).build()

    async def _send_long(update: Update, text: str) -> None:
        for i in range(0, len(text), 4096):
            await update.message.reply_text(
                text[i : i + 4096], parse_mode="Markdown"
            )

    async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        user_id = str(update.effective_user.id)
        text = update.message.text or ""

        # Admin check if configured
        if TELEGRAM_ADMIN_ID and user_id != TELEGRAM_ADMIN_ID:
            await update.message.reply_text("Access denied.")
            return

        # Check if we're waiting for a credential value
        if chat_id in pending:
            label, _ = pending.pop(chat_id)
            resp, new_creds = await orchestrator.process_message(
                user_id, text, provide_cred=(label, text)
            )
            await _send_long(update, resp)
            if new_creds:
                label2, desc2 = new_creds[0]
                pending[chat_id] = (label2, desc2)
                await _send_long(update, f"🔑 Please provide `{label2}`:\n_{desc2}_")
            return

        resp, cred_requests = await orchestrator.process_message(user_id, text)
        await _send_long(update, resp)

        if cred_requests:
            label, desc = cred_requests[0]
            pending[chat_id] = (label, desc)
            await _send_long(update, f"🔑 I need a credential.\nPlease provide `{label}`:\n_{desc}_")

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_handler(CommandHandler("start", on_message))
    app.add_handler(CommandHandler("help", on_message))
    app.add_handler(CommandHandler("leaderboard", on_message))
    app.add_handler(CommandHandler("gamestatus", on_message))
    app.add_handler(CommandHandler("lastbattle", on_message))
    app.add_handler(CommandHandler("creds", on_message))

    return app


# ═══════════════════════════════════════════════════════════════════════════ #
# CLI Mode                                                                    #
# ═══════════════════════════════════════════════════════════════════════════ #

async def run_cli(orchestrator: MirAI_Orchestrator) -> None:
    print("MirAI_OS – Interactive CLI")
    print("Type /help for commands, Ctrl+C to quit.\n")

    pending_cred: Optional[Tuple[str, str]] = None   # (label, description)
    user_id = "cli_user"

    while True:
        try:
            if pending_cred:
                label, desc = pending_cred
                value = getpass.getpass(f"🔑 Enter {label} ({desc}): ")
                resp, new_creds = await orchestrator.process_message(
                    user_id, "", provide_cred=(label, value)
                )
                print(f"\nMirAI: {resp}\n")
                pending_cred = new_creds[0] if new_creds else None
            else:
                text = input("You: ").strip()
                if not text:
                    continue
                resp, cred_requests = await orchestrator.process_message(user_id, text)
                print(f"\nMirAI: {resp}\n")
                pending_cred = cred_requests[0] if cred_requests else None
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye. El Psy Kongroo.")
            break


# ═══════════════════════════════════════════════════════════════════════════ #
# Entry Point                                                                 #
# ═══════════════════════════════════════════════════════════════════════════ #

async def main() -> None:
    orchestrator = MirAI_Orchestrator()

    # Start game engine in background
    game_task = asyncio.create_task(orchestrator.game.run())

    mode = "telegram" if "--telegram" in sys.argv else "cli"

    if mode == "telegram":
        if not _TG_OK:
            print("ERROR: python-telegram-bot not installed. Run: pip install python-telegram-bot")
            return
        bot_token = TELEGRAM_BOT_TOKEN
        if not bot_token:
            bot_token = input("Enter TELEGRAM_BOT_TOKEN: ").strip()
            orchestrator.creds.set("TELEGRAM_BOT_TOKEN", bot_token)
            os.environ["TELEGRAM_BOT_TOKEN"] = bot_token
        tg_app = build_telegram_app(orchestrator, bot_token=bot_token)
        logger.info("Starting Telegram bot…")
        async with tg_app:
            await tg_app.start()
            await tg_app.updater.start_polling()
            try:
                await asyncio.Event().wait()   # run forever
            finally:
                await tg_app.updater.stop()
                await tg_app.stop()
    else:
        await run_cli(orchestrator)

    game_task.cancel()
    try:
        await game_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
