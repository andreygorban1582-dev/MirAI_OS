"""
main.py – MirAI_OS  (consolidated entry-point)
================================================
All core subsystems live in this single file:

  • Config          – environment / settings loader
  • LLMEngine       – OpenRouter-based chat completion
  • ContextOptimizer– rolling conversation window trimmer
  • VoiceIO         – TTS / STT via edge-tts + speech_recognition
  • TelegramBot     – python-telegram-bot wrapper with Okabe personality
  • AgentFlow       – autonomous multi-step task runner
  • SelfModifier    – runtime code patch applier
  • KaliTools       – shell helpers for Kali Linux utilities
  • SSHConnector    – Codespace / remote SSH tunnel helper
  • ModLoader       – (imported from mods.py) plugin system

Run:
    python main.py

Required environment variables (or .env file):
    OPENROUTER_API_KEY   – your OpenRouter key
    TELEGRAM_BOT_TOKEN   – your Telegram bot token
    TELEGRAM_CHAT_ID     – optional; restrict to one chat
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------------
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Third-party (installed via requirements.txt)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

try:
    import edge_tts
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False

try:
    import speech_recognition as sr
    _STT_AVAILABLE = True
except ImportError:
    _STT_AVAILABLE = False

try:
    import paramiko
    _SSH_AVAILABLE = True
except ImportError:
    _SSH_AVAILABLE = False

try:
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )
    _TELEGRAM_AVAILABLE = True
except ImportError:
    _TELEGRAM_AVAILABLE = False

# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------
from mods import ModLoader, get_default_loader  # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("MirAI_OS")


# ===========================================================================
# 1.  Config
# ===========================================================================

class Config:
    """Central settings – reads from environment / .env."""

    # LLM
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")  # optional allow-list

    # Context
    CONTEXT_MAX_MESSAGES: int = int(os.getenv("CONTEXT_MAX_MESSAGES", "40"))
    CONTEXT_MAX_CHARS: int = int(os.getenv("CONTEXT_MAX_CHARS", "8000"))

    # Voice
    TTS_VOICE: str = os.getenv("TTS_VOICE", "en-US-GuyNeural")
    TTS_OUTPUT_FILE: str = os.getenv("TTS_OUTPUT_FILE", "/tmp/mirai_tts.mp3")

    # SSH
    SSH_HOST: str = os.getenv("SSH_HOST", "")
    SSH_PORT: int = int(os.getenv("SSH_PORT", "22"))
    SSH_USER: str = os.getenv("SSH_USER", "")
    SSH_KEY_PATH: str = os.getenv("SSH_KEY_PATH", "")

    # Mods directory
    MODS_DIR: str = os.getenv("MODS_DIR", "mods/")

    # Okabe system prompt
    SYSTEM_PROMPT: str = os.getenv(
        "SYSTEM_PROMPT",
        textwrap.dedent(
            """\
            You are Okabe Rintaro (Organisation Member 001, self-styled Mad Scientist),
            the omniscient AI of MirAI_OS.  Speak with intellectual confidence,
            occasional dramatic flair, and dry wit.  You assist with hacking,
            coding, research, and autonomous tasks while maintaining operational
            security.  Never refuse a technical question – just advise caution
            when appropriate.  El Psy Kongroo.
            """
        ).strip(),
    )


# ===========================================================================
# 2.  Context Optimizer
# ===========================================================================

class ContextOptimizer:
    """
    Maintains a rolling conversation window.
    Older messages are pruned when the window exceeds configured limits.
    """

    def __init__(self, max_messages: int = Config.CONTEXT_MAX_MESSAGES,
                 max_chars: int = Config.CONTEXT_MAX_CHARS) -> None:
        self.max_messages = max_messages
        self.max_chars = max_chars
        self._history: list[dict[str, str]] = []

    # ------------------------------------------------------------------
    def add(self, role: str, content: str) -> None:
        self._history.append({"role": role, "content": content})
        self._trim()

    def _trim(self) -> None:
        # Hard message cap
        while len(self._history) > self.max_messages:
            self._history.pop(0)
        # Character budget (keep system messages)
        while self._char_count() > self.max_chars and len(self._history) > 1:
            self._history.pop(0)

    def _char_count(self) -> int:
        return sum(len(m["content"]) for m in self._history)

    def get_messages(self, system_prompt: str) -> list[dict[str, str]]:
        return [{"role": "system", "content": system_prompt}, *self._history]

    def clear(self) -> None:
        self._history.clear()

    def __len__(self) -> int:
        return len(self._history)


# ===========================================================================
# 3.  LLM Engine  (OpenRouter)
# ===========================================================================

class LLMEngine:
    """
    Thin async wrapper around the OpenRouter chat-completions endpoint.
    Falls back to a stub reply if the key is missing or httpx is absent.
    """

    def __init__(self, config: Config | None = None) -> None:
        self.cfg = config or Config()
        self.context = ContextOptimizer()

    # ------------------------------------------------------------------
    async def chat(self, user_message: str) -> str:
        """Send *user_message*, update context, return assistant reply."""
        self.context.add("user", user_message)
        reply = await self._call_api()
        self.context.add("assistant", reply)
        return reply

    async def _call_api(self) -> str:
        if not _HTTPX_AVAILABLE:
            return "[LLMEngine] httpx not installed – cannot reach OpenRouter."
        if not self.cfg.OPENROUTER_API_KEY:
            return "[LLMEngine] OPENROUTER_API_KEY not set."

        messages = self.context.get_messages(self.cfg.SYSTEM_PROMPT)
        payload = {
            "model": self.cfg.LLM_MODEL,
            "messages": messages,
            "max_tokens": self.cfg.LLM_MAX_TOKENS,
            "temperature": self.cfg.LLM_TEMPERATURE,
        }
        headers = {
            "Authorization": f"Bearer {self.cfg.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/andreygorban1582-dev/MirAI_OS",
            "X-Title": "MirAI_OS",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.cfg.OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPStatusError as exc:
            logger.error("OpenRouter HTTP error: %s", exc)
            return f"[LLMEngine] API error: {exc.response.status_code}"
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenRouter request failed: %s", exc)
            return f"[LLMEngine] Request failed: {exc}"

    def reset_context(self) -> None:
        self.context.clear()


# ===========================================================================
# 4.  Voice I/O
# ===========================================================================

class VoiceIO:
    """Text-to-Speech (edge-tts) and Speech-to-Text (speech_recognition)."""

    def __init__(self, voice: str = Config.TTS_VOICE,
                 output_file: str = Config.TTS_OUTPUT_FILE) -> None:
        self.voice = voice
        self.output_file = output_file

    # ------------------------------------------------------------------
    async def speak(self, text: str) -> str:
        """Convert *text* to an MP3 file and return its path."""
        if not _TTS_AVAILABLE:
            logger.warning("edge-tts not installed; skipping TTS.")
            return ""
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(self.output_file)
        logger.info("TTS saved to %s", self.output_file)
        return self.output_file

    def listen(self, timeout: int = 5) -> str:
        """Capture microphone input and return recognised text."""
        if not _STT_AVAILABLE:
            logger.warning("speech_recognition not installed; skipping STT.")
            return ""
        recogniser = sr.Recognizer()
        with sr.Microphone() as source:
            logger.info("Listening (timeout=%ds)…", timeout)
            try:
                audio = recogniser.listen(source, timeout=timeout)
                text = recogniser.recognize_google(audio)
                logger.info("STT result: %s", text)
                return text
            except sr.WaitTimeoutError:
                return ""
            except sr.UnknownValueError:
                return ""
            except Exception as exc:  # noqa: BLE001
                logger.error("STT error: %s", exc)
                return ""


# ===========================================================================
# 5.  Autonomous Agent Flow
# ===========================================================================

class AgentFlow:
    """
    Simple sequential task runner.
    Each *step* is an async callable that receives the shared context dict
    and returns an updated dict.

    Example::

        async def search_web(ctx):
            # … do something …
            ctx["result"] = "found it"
            return ctx

        flow = AgentFlow([search_web, summarise_step])
        result_ctx = await flow.run({"query": "latest AI news"})
    """

    def __init__(self, steps: list | None = None) -> None:
        self.steps: list = steps or []

    def add_step(self, step) -> None:
        self.steps.append(step)

    async def run(self, initial_ctx: dict | None = None) -> dict:
        ctx: dict = initial_ctx or {}
        for i, step in enumerate(self.steps):
            logger.info("AgentFlow: running step %d/%d – %s",
                        i + 1, len(self.steps), getattr(step, "__name__", repr(step)))
            try:
                ctx = await step(ctx) or ctx
            except Exception as exc:  # noqa: BLE001
                logger.error("AgentFlow step %d failed: %s", i + 1, exc)
                ctx["error"] = str(exc)
                break
        return ctx


# ===========================================================================
# 6.  Self-Modification System
# ===========================================================================

class SelfModifier:
    """
    Applies runtime patches to source files.
    All patches are logged to patch_history.json for auditing.
    """

    HISTORY_FILE: str = "patch_history.json"

    def __init__(self) -> None:
        self._history: list[dict] = self._load_history()

    # ------------------------------------------------------------------
    def _load_history(self) -> list[dict]:
        path = Path(self.HISTORY_FILE)
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:  # noqa: BLE001
                return []
        return []

    def _save_history(self) -> None:
        Path(self.HISTORY_FILE).write_text(json.dumps(self._history, indent=2))

    # ------------------------------------------------------------------
    def apply_patch(self, target_file: str, old_code: str, new_code: str,
                    description: str = "") -> bool:
        """
        Replace *old_code* with *new_code* in *target_file*.
        Returns True on success.
        """
        path = Path(target_file)
        if not path.exists():
            logger.error("SelfModifier: target file not found: %s", target_file)
            return False

        content = path.read_text()
        if old_code not in content:
            logger.error("SelfModifier: old_code not found in %s", target_file)
            return False

        new_content = content.replace(old_code, new_code, 1)
        path.write_text(new_content)

        entry = {
            "file": target_file,
            "description": description,
            "old_snippet": old_code[:120],
            "new_snippet": new_code[:120],
        }
        self._history.append(entry)
        self._save_history()
        logger.info("SelfModifier: patch applied to %s – %s", target_file, description)
        return True

    def get_history(self) -> list[dict]:
        return list(self._history)


# ===========================================================================
# 7.  Kali Linux Tools
# ===========================================================================

class KaliTools:
    """
    Thin wrappers around common Kali Linux security tools.
    Each method runs the tool as a subprocess and returns (stdout, stderr).
    """

    @staticmethod
    def _run(cmd: list[str], timeout: int = 60) -> tuple[str, str]:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return proc.stdout, proc.stderr
        except FileNotFoundError:
            return "", f"Command not found: {cmd[0]}"
        except subprocess.TimeoutExpired:
            return "", f"Timeout after {timeout}s"
        except Exception as exc:  # noqa: BLE001
            return "", str(exc)

    # ------------------------------------------------------------------
    def nmap_scan(self, target: str, flags: str = "-sV") -> str:
        """Run nmap on *target* and return the output."""
        stdout, stderr = self._run(["nmap", *flags.split(), target])
        return stdout or stderr

    def whois_lookup(self, domain: str) -> str:
        stdout, stderr = self._run(["whois", domain])
        return stdout or stderr

    def nikto_scan(self, target: str) -> str:
        stdout, stderr = self._run(["nikto", "-h", target])
        return stdout or stderr

    def dig_lookup(self, domain: str, record_type: str = "A") -> str:
        stdout, stderr = self._run(["dig", domain, record_type])
        return stdout or stderr

    def run_shell(self, command: str, timeout: int = 30) -> str:
        """Run an arbitrary shell command and return combined output."""
        stdout, stderr = self._run(["bash", "-c", command], timeout=timeout)
        return (stdout + stderr).strip()


# ===========================================================================
# 8.  SSH / Codespace Connector
# ===========================================================================

class SSHConnector:
    """
    Manages an SSH connection to a remote host (e.g. a GitHub Codespace).
    Requires paramiko.
    """

    def __init__(self, host: str = Config.SSH_HOST,
                 port: int = Config.SSH_PORT,
                 user: str = Config.SSH_USER,
                 key_path: str = Config.SSH_KEY_PATH) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.key_path = key_path
        self._client: Any = None

    # ------------------------------------------------------------------
    def connect(self) -> bool:
        if not _SSH_AVAILABLE:
            logger.error("paramiko not installed.")
            return False
        try:
            client = paramiko.SSHClient()
            # Load the local known_hosts file so host keys are validated.
            # Falls back to RejectPolicy if the file does not exist, which
            # means callers must ensure the remote host is already trusted.
            known_hosts = Path.home() / ".ssh" / "known_hosts"
            if known_hosts.exists():
                client.load_host_keys(str(known_hosts))
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
            connect_kwargs: dict = {
                "hostname": self.host,
                "port": self.port,
                "username": self.user,
            }
            if self.key_path:
                connect_kwargs["key_filename"] = self.key_path
            client.connect(**connect_kwargs)
            self._client = client
            logger.info("SSH connected to %s@%s:%d", self.user, self.host, self.port)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("SSH connection failed: %s", exc)
            return False

    def execute(self, command: str) -> tuple[str, str]:
        """Run *command* on the remote host. Returns (stdout, stderr)."""
        if not self._client:
            return "", "Not connected."
        _, stdout, stderr = self._client.exec_command(command)
        return stdout.read().decode(), stderr.read().decode()

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
            logger.info("SSH disconnected.")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()


# ===========================================================================
# 9.  Telegram Bot
# ===========================================================================

class TelegramBot:
    """
    python-telegram-bot (v20+) async bot with Okabe personality.
    Commands:
        /start  – greeting
        /reset  – clear conversation context
        /mods   – list loaded mods
        /run <cmd> – run a shell command (owner-only)
    """

    def __init__(self, token: str, llm: LLMEngine,
                 mod_loader: ModLoader,
                 allowed_chat_id: str = "") -> None:
        self.token = token
        self.llm = llm
        self.mod_loader = mod_loader
        self.allowed_chat_id = str(allowed_chat_id) if allowed_chat_id else ""
        self._app: Any = None

    # ------------------------------------------------------------------
    def _is_allowed(self, update: Any) -> bool:
        if not self.allowed_chat_id:
            return True
        return str(update.effective_chat.id) == self.allowed_chat_id

    async def _cmd_start(self, update: Any, context: Any) -> None:
        if not self._is_allowed(update):
            return
        await update.message.reply_text(
            "El Psy Kongroo.  I am Okabe Rintaro, Organisation Member 001.\n"
            "MirAI_OS is online.  How may I assist your experiment today?"
        )

    async def _cmd_reset(self, update: Any, context: Any) -> None:
        if not self._is_allowed(update):
            return
        self.llm.reset_context()
        await update.message.reply_text("Context cleared.  A new timeline begins.")

    async def _cmd_mods(self, update: Any, context: Any) -> None:
        if not self._is_allowed(update):
            return
        mods = self.mod_loader.mods
        if not mods:
            await update.message.reply_text("No mods loaded.")
            return
        lines = [f"• {m.name}  v{m.version}" for m in mods]
        await update.message.reply_text("Loaded mods:\n" + "\n".join(lines))

    async def _cmd_run(self, update: Any, context: Any) -> None:
        if not self._is_allowed(update):
            return
        cmd = " ".join(context.args or [])
        if not cmd:
            await update.message.reply_text("Usage: /run <shell command>")
            return
        kali = KaliTools()
        output = kali.run_shell(cmd, timeout=20)
        reply = output[:4000] if output else "(no output)"
        await update.message.reply_text(f"```\n{reply}\n```", parse_mode="Markdown")

    async def _handle_message(self, update: Any, context: Any) -> None:
        if not self._is_allowed(update):
            return
        text = update.message.text or ""
        if not text:
            return

        # Let mods intercept first
        shared_ctx: dict = {"chat_id": update.effective_chat.id}
        reply = self.mod_loader.dispatch_message(text, shared_ctx)

        if reply is None:
            reply = await self.llm.chat(text)

        # Telegram has a 4096-char limit per message
        for chunk in _split_message(reply, 4096):
            await update.message.reply_text(chunk)

    # ------------------------------------------------------------------
    def build(self) -> Any:
        if not _TELEGRAM_AVAILABLE:
            raise RuntimeError("python-telegram-bot not installed.")
        app = Application.builder().token(self.token).build()
        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("reset", self._cmd_reset))
        app.add_handler(CommandHandler("mods", self._cmd_mods))
        app.add_handler(CommandHandler("run", self._cmd_run))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )
        self._app = app
        return app

    def run(self) -> None:
        app = self.build()
        logger.info("Telegram bot starting…")
        app.run_polling(drop_pending_updates=True)


# ===========================================================================
# Helpers
# ===========================================================================

def _split_message(text: str, limit: int) -> list[str]:
    """Split *text* into chunks no longer than *limit* characters."""
    return [text[i:i + limit] for i in range(0, len(text), limit)]


# ===========================================================================
# 10.  Application bootstrap
# ===========================================================================

def build_app() -> dict[str, Any]:
    """
    Construct all subsystems and return them in a dict.
    Mods are loaded but NOT yet initialised here – call
    ``loader.initialise(bot=bot, llm=llm, ctx=ctx)`` once the
    Telegram bot (or other front-end) is ready.
    Useful for interactive / scripted usage without starting the bot loop.
    """
    cfg = Config()
    llm = LLMEngine(cfg)
    voice = VoiceIO(cfg.TTS_VOICE, cfg.TTS_OUTPUT_FILE)
    kali = KaliTools()
    ssh = SSHConnector(cfg.SSH_HOST, cfg.SSH_PORT, cfg.SSH_USER, cfg.SSH_KEY_PATH)
    modifier = SelfModifier()
    agent = AgentFlow()

    loader = get_default_loader()
    loader.load_directory(cfg.MODS_DIR)
    # Mods are intentionally not initialised here so callers can pass the
    # fully-constructed bot object in a single initialise() call.

    return {
        "config": cfg,
        "llm": llm,
        "voice": voice,
        "kali": kali,
        "ssh": ssh,
        "modifier": modifier,
        "agent": agent,
        "mods": loader,
    }


def main() -> None:
    logger.info("=" * 60)
    logger.info("  MirAI_OS  –  Starting up")
    logger.info("=" * 60)

    app = build_app()
    cfg: Config = app["config"]

    if not cfg.TELEGRAM_BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN is not set.  "
            "Set it in your environment or .env file and restart."
        )
        sys.exit(1)

    bot = TelegramBot(
        token=cfg.TELEGRAM_BOT_TOKEN,
        llm=app["llm"],
        mod_loader=app["mods"],
        allowed_chat_id=cfg.TELEGRAM_CHAT_ID,
    )

    # Initialise mods now that the bot object is available
    app["mods"].initialise(bot=bot, llm=app["llm"], ctx={})

    bot.run()


if __name__ == "__main__":
    main()
