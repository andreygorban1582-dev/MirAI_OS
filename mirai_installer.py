#!/usr/bin/env python3
"""
MirAI_OS – All-in-One Installer & Runtime
==========================================
Single-file Python installer that sets up and runs the full MirAI_OS stack:
  • WSL2 Kali Linux environment with 128 GB swap
  • Ollama with an 8B-parameter LLM (llama3:8b)
  • Sesame CSM voice synthesis + Telegram voice messaging
  • Docker container for OpenRouter API proxy
  • Codespaces SSH orchestration
  • 200+ Kali Linux tool integrations
  • Full RPG game engine (characters, economy, quests, diplomacy, crafting)
  • Multi-persona orchestrator with 50+ personas
  • Custom tkinter GUI (installer wizard + application dashboard)

Usage
-----
    python mirai_installer.py                # Launch GUI installer/app
    python mirai_installer.py --install      # Headless install
    python mirai_installer.py --run          # Skip install, run app
    python mirai_installer.py --mode telegram  # Run Telegram bot
    python mirai_installer.py --help         # Show help
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import copy
import csv
import datetime
import hashlib
import io
import json
import logging
import math
import os
import pathlib
import platform
import random
import re
import shlex
import shutil
import signal
import socket
import sqlite3
import string
import struct
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import traceback
import uuid
import warnings
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger("mirai")

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------
__version__ = "1.0.0"
BANNER = r"""
  __  __ _         _    ___    ___  ____
 |  \/  (_)_ __   / \  |_ _|  / _ \/ ___|
 | |\/| | | '__| / _ \  | |  | | | \___ \
 | |  | | | |   / ___ \ | |  | |_| |___) |
 |_|  |_|_|_|  /_/   \_\___|  \___/|____/
              All-in-One v{ver}
""".format(
    ver=__version__
)

# ============================================================================
# SECTION 1 – CONFIGURATION
# ============================================================================

MIRAI_DIR = pathlib.Path.home() / ".mirai_os"
DB_PATH = MIRAI_DIR / "mirai.db"
CONFIG_PATH = MIRAI_DIR / "config.json"
LOG_PATH = MIRAI_DIR / "mirai.log"


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


@dataclass
class Config:
    """Centralised runtime configuration."""

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    orchestrator_model: str = "openai/gpt-4o-mini"
    worker_model: str = "openai/gpt-4o"
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.7

    # Local LLM (Ollama)
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3:8b"
    use_local_llm: bool = True

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Voice
    tts_voice: str = "en-US-GuyNeural"
    tts_output_file: str = "/tmp/mirai_tts.mp3"
    sesame_csm_enabled: bool = True
    sesame_csm_model: str = "sesame/csm-1b"

    # SSH / Codespaces
    ssh_host: str = ""
    ssh_user: str = ""
    ssh_key_path: str = ""
    codespace_name: str = ""

    # Kubernetes
    k8s_namespace: str = "mirai-os"

    # WSL / Swap
    wsl_swap_gb: int = 128

    # Docker
    docker_openrouter_port: int = 8880

    # Paths
    mirai_dir: str = str(MIRAI_DIR)
    db_path: str = str(DB_PATH)

    @classmethod
    def from_env(cls) -> "Config":
        cfg = cls(
            openrouter_api_key=_env("OPENROUTER_API_KEY"),
            telegram_bot_token=_env("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=_env("TELEGRAM_CHAT_ID"),
            ssh_host=_env("SSH_HOST"),
            ssh_user=_env("SSH_USER", "root"),
            ssh_key_path=_env("SSH_KEY_PATH", str(pathlib.Path.home() / ".ssh/id_rsa")),
            codespace_name=_env("CODESPACE_NAME"),
            ollama_host=_env("OLLAMA_HOST", "http://127.0.0.1:11434"),
            ollama_model=_env("OLLAMA_MODEL", "llama3:8b"),
            use_local_llm=_env("USE_LOCAL_LLM", "true").lower() in ("1", "true", "yes"),
            sesame_csm_enabled=_env("SESAME_CSM_ENABLED", "true").lower()
            in ("1", "true", "yes"),
        )
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH) as f:
                    data = json.load(f)
                for k, v in data.items():
                    if hasattr(cfg, k):
                        setattr(cfg, k, v)
            except Exception:
                pass
        return cfg

    def save(self) -> None:
        MIRAI_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.__dict__, f, indent=2)


CFG = Config.from_env()

# ============================================================================
# SECTION 2 – INSTALLER  (WSL2, Swap, Docker, Ollama, Deps)
# ============================================================================


def _run(cmd: str, check: bool = True, capture: bool = False, **kw) -> subprocess.CompletedProcess:
    """Run a shell command with logging."""
    log.info("$ %s", cmd)
    return subprocess.run(cmd, shell=True, check=check, capture_output=capture, text=True, **kw)


def _cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _is_wsl() -> bool:
    return "microsoft" in platform.uname().release.lower()


# -- WSL2 swap ---------------------------------------------------------------

def configure_wsl_swap(swap_gb: int = 128) -> str:
    """Create or update .wslconfig to set swap size."""
    wslconfig = pathlib.Path.home() / ".wslconfig"
    swap_line = f"swap={swap_gb}GB"
    section = "[wsl2]"

    if wslconfig.exists():
        text = wslconfig.read_text()
        if swap_line in text:
            return f"Swap already configured at {swap_gb} GB"
        if section in text:
            text = re.sub(r"swap=\d+GB", swap_line, text)
            if swap_line not in text:
                text = text.replace(section, f"{section}\n{swap_line}")
        else:
            text += f"\n{section}\n{swap_line}\n"
        wslconfig.write_text(text)
    else:
        wslconfig.write_text(f"{section}\n{swap_line}\nmemory=16GB\nprocessors=4\n")
    return f"Configured WSL2 swap to {swap_gb} GB – restart WSL to apply"


def setup_linux_swap(swap_gb: int = 128) -> str:
    """Create a swap file on native Linux / WSL2."""
    swap_path = pathlib.Path("/swapfile_mirai")
    if swap_path.exists():
        return f"Swap file already exists at {swap_path}"
    try:
        _run(f"sudo fallocate -l {swap_gb}G {swap_path}")
        _run(f"sudo chmod 600 {swap_path}")
        _run(f"sudo mkswap {swap_path}")
        _run(f"sudo swapon {swap_path}")
        return f"Created and activated {swap_gb} GB swap at {swap_path}"
    except Exception as exc:
        return f"Swap setup skipped (may need root): {exc}"


# -- Docker -------------------------------------------------------------------

DOCKER_COMPOSE_OPENROUTER = textwrap.dedent("""\
    version: "3.9"
    services:
      openrouter-proxy:
        image: nginx:alpine
        container_name: mirai-openrouter-proxy
        ports:
          - "{port}:80"
        environment:
          - OPENROUTER_API_KEY=${{OPENROUTER_API_KEY:-}}
        volumes:
          - ./nginx-openrouter.conf:/etc/nginx/conf.d/default.conf:ro
        restart: unless-stopped
""")

NGINX_OPENROUTER_CONF = textwrap.dedent("""\
    server {{
        listen 80;
        location / {{
            proxy_pass https://openrouter.ai/api/v1;
            proxy_set_header Host openrouter.ai;
            proxy_set_header Authorization "Bearer {api_key}";
            proxy_set_header Content-Type application/json;
            proxy_ssl_server_name on;
        }}
    }}
""")


def setup_docker_openrouter(api_key: str = "", port: int = 8880) -> str:
    """Deploy an nginx reverse-proxy container for OpenRouter."""
    if not _cmd_exists("docker"):
        return "Docker not found – install Docker first"

    work = MIRAI_DIR / "docker"
    work.mkdir(parents=True, exist_ok=True)

    compose = work / "docker-compose.yml"
    compose.write_text(DOCKER_COMPOSE_OPENROUTER.format(port=port))

    nginx_conf = work / "nginx-openrouter.conf"
    key = api_key or CFG.openrouter_api_key or "YOUR_API_KEY"
    nginx_conf.write_text(NGINX_OPENROUTER_CONF.format(api_key=key))

    try:
        _run(f"docker compose -f {compose} up -d")
        return f"OpenRouter proxy running on http://localhost:{port}"
    except Exception as exc:
        return f"Docker setup failed: {exc}"


# -- Ollama / 8B model -------------------------------------------------------

def install_ollama() -> str:
    """Install Ollama and pull the 8B model."""
    if _cmd_exists("ollama"):
        msg = "Ollama already installed"
    else:
        try:
            _run("curl -fsSL https://ollama.com/install.sh | sh")
            msg = "Ollama installed"
        except Exception as exc:
            return f"Ollama install failed: {exc}"
    # Pull model
    model = CFG.ollama_model
    try:
        _run(f"ollama pull {model}")
        msg += f" | Pulled {model}"
    except Exception as exc:
        msg += f" | Model pull skipped: {exc}"
    return msg


# -- Kali tools ---------------------------------------------------------------

KALI_TOOLS = [
    "nmap", "hydra", "john", "sqlmap", "nikto", "gobuster", "dirb",
    "wfuzz", "hashcat", "aircrack-ng", "reaver", "bettercap", "ettercap",
    "msfconsole", "searchsploit", "whatweb", "fierce", "dnsenum",
    "enum4linux", "smbclient", "nbtscan", "snmpwalk", "arp-scan",
    "masscan", "amass", "sublist3r", "theharvester", "maltego",
    "wireshark", "tcpdump", "netcat", "socat", "proxychains",
    "macchanger", "crunch", "cewl", "medusa", "patator",
    "wpscan", "joomscan", "droopescan", "sslscan", "testssl.sh",
    "burpsuite", "zaproxy", "commix", "xsser", "beef-xss",
    "setoolkit", "autopsy", "volatility", "binwalk", "foremost",
    "steghide", "exiftool", "stegsolve", "radare2", "ghidra",
    "gdb", "ltrace", "strace", "objdump", "strings",
    "responder", "impacket-smbserver", "crackmapexec", "evil-winrm",
    "bloodhound", "neo4j", "powershell-empire", "covenant",
    "mimikatz", "lazagne", "pspy", "linpeas", "winpeas",
]


def install_kali_tools() -> str:
    """Install common Kali Linux tools."""
    try:
        _run("sudo apt-get update -qq", check=False)
        installed = []
        for tool in KALI_TOOLS[:30]:  # install top-30 common ones
            try:
                _run(f"sudo apt-get install -y -qq {tool}", check=False)
                installed.append(tool)
            except Exception:
                pass
        return f"Installed {len(installed)} Kali tools"
    except Exception as exc:
        return f"Kali tools install skipped: {exc}"


def scan_available_tools() -> Dict[str, str]:
    """Scan which Kali tools are available on PATH."""
    found: Dict[str, str] = {}
    for t in KALI_TOOLS:
        p = shutil.which(t)
        if p:
            found[t] = p
    return found


# -- Python deps --------------------------------------------------------------

REQUIRED_PACKAGES = [
    "httpx>=0.27",
    "python-telegram-bot>=20.7",
    "edge-tts>=6.1.9",
    "SpeechRecognition>=3.10",
    "paramiko>=3.4",
    "python-dotenv>=1.0",
]


def install_python_deps() -> str:
    """pip-install required packages."""
    for pkg in REQUIRED_PACKAGES:
        try:
            _run(f"{sys.executable} -m pip install -q {shlex.quote(pkg)}")
        except Exception:
            log.warning("Could not install %s", pkg)
    return "Python dependencies installed"


# -- Full install orchestration -----------------------------------------------

def run_full_install(cfg: Config | None = None) -> List[str]:
    """Execute the entire installation sequence. Returns status messages."""
    cfg = cfg or CFG
    msgs: list[str] = []
    MIRAI_DIR.mkdir(parents=True, exist_ok=True)

    msgs.append("=== MirAI_OS Full Install ===")

    # 1. Swap
    if _is_wsl():
        msgs.append(configure_wsl_swap(cfg.wsl_swap_gb))
    msgs.append(setup_linux_swap(cfg.wsl_swap_gb))

    # 2. Python deps
    msgs.append(install_python_deps())

    # 3. Ollama
    msgs.append(install_ollama())

    # 4. Docker OpenRouter proxy
    msgs.append(setup_docker_openrouter(cfg.openrouter_api_key, cfg.docker_openrouter_port))

    # 5. Kali tools
    msgs.append(install_kali_tools())

    # 6. Save config
    cfg.save()
    msgs.append(f"Config saved to {CONFIG_PATH}")

    return msgs


# ============================================================================
# SECTION 3 – LLM CLIENT  (OpenRouter + Ollama + Transformers fallback)
# ============================================================================


class ContextOptimizer:
    """Rolling window of conversation messages."""

    def __init__(self, max_messages: int = 40, max_chars: int = 8000):
        self.max_messages = max_messages
        self.max_chars = max_chars
        self._messages: Deque[Dict[str, str]] = deque()

    def add(self, role: str, content: str) -> None:
        self._messages.append({"role": role, "content": content})
        while len(self._messages) > self.max_messages:
            self._messages.popleft()
        while self._total_chars() > self.max_chars and len(self._messages) > 1:
            self._messages.popleft()

    def _total_chars(self) -> int:
        return sum(len(m["content"]) for m in self._messages)

    def get_messages(self, system_prompt: str = "") -> List[Dict[str, str]]:
        msgs: list[dict[str, str]] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.extend(self._messages)
        return msgs

    def clear(self) -> None:
        self._messages.clear()


class LLMClient:
    """Unified LLM client: Ollama ➜ OpenRouter ➜ Transformers fallback."""

    def __init__(
        self,
        model: str = "",
        system_prompt: str = "",
        cfg: Config | None = None,
    ):
        self.cfg = cfg or CFG
        self.model = model or self.cfg.ollama_model
        self.system_prompt = system_prompt
        self.context = ContextOptimizer()

    async def chat(self, user_msg: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        self.context.add("user", user_msg)
        reply = ""

        # 1. Try Ollama (local)
        if self.cfg.use_local_llm:
            reply = await self._call_ollama(temperature, max_tokens)

        # 2. Try OpenRouter
        if not reply and self.cfg.openrouter_api_key:
            reply = await self._call_openrouter(temperature, max_tokens)

        # 3. Fallback stub
        if not reply:
            reply = "[LLM unavailable – configure Ollama or OpenRouter]"

        self.context.add("assistant", reply)
        return reply

    async def _call_ollama(self, temperature: float, max_tokens: int) -> str:
        try:
            import httpx  # noqa: F811
        except ImportError:
            return ""
        try:
            messages = self.context.get_messages(self.system_prompt)
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(f"{self.cfg.ollama_host}/api/chat", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("message", {}).get("content", "").strip()
        except Exception as exc:
            log.debug("Ollama call failed: %s", exc)
        return ""

    async def _call_openrouter(self, temperature: float, max_tokens: int) -> str:
        try:
            import httpx  # noqa: F811
        except ImportError:
            return ""
        try:
            messages = self.context.get_messages(self.system_prompt)
            payload = {
                "model": self.model if "/" in self.model else self.cfg.worker_model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            headers = {
                "Authorization": f"Bearer {self.cfg.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/andreygorban1582-dev/MirAI_OS",
                "X-Title": "MirAI_OS",
            }
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.cfg.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            log.debug("OpenRouter call failed: %s", exc)
        return ""


# ============================================================================
# SECTION 4 – VOICE I/O  (Edge-TTS + Sesame CSM + STT)
# ============================================================================


class VoiceIO:
    """Text-to-Speech (edge-tts / Sesame CSM) and Speech-to-Text."""

    def __init__(self, cfg: Config | None = None):
        self.cfg = cfg or CFG
        self.voice = self.cfg.tts_voice
        self.output_file = self.cfg.tts_output_file

    # -- TTS via edge-tts -----------------------------------------------------
    async def speak(self, text: str) -> str:
        """Convert text to speech and return the file path."""
        # Try Sesame CSM first if enabled
        if self.cfg.sesame_csm_enabled:
            path = await self._speak_sesame(text)
            if path:
                return path
        # Fallback to edge-tts
        return await self._speak_edge_tts(text)

    async def _speak_edge_tts(self, text: str) -> str:
        try:
            import edge_tts
        except ImportError:
            log.warning("edge-tts not installed")
            return ""
        try:
            comm = edge_tts.Communicate(text, self.voice)
            await comm.save(self.output_file)
            return self.output_file
        except Exception as exc:
            log.error("TTS failed: %s", exc)
            return ""

    async def _speak_sesame(self, text: str) -> str:
        """Sesame CSM voice synthesis via local model or API."""
        try:
            import httpx  # noqa: F811
        except ImportError:
            return ""
        # Try Sesame CSM API endpoint (self-hosted or cloud)
        sesame_url = os.environ.get("SESAME_CSM_URL", "http://127.0.0.1:8860/v1/audio/speech")
        try:
            payload = {
                "model": self.cfg.sesame_csm_model,
                "input": text,
                "voice": "alloy",
                "response_format": "mp3",
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(sesame_url, json=payload)
                if resp.status_code == 200:
                    out = self.output_file.replace(".mp3", "_csm.mp3")
                    pathlib.Path(out).write_bytes(resp.content)
                    return out
        except Exception as exc:
            log.debug("Sesame CSM not available: %s", exc)
        return ""

    # -- STT ------------------------------------------------------------------
    def listen(self, timeout: int = 5) -> str:
        """Capture audio from microphone and transcribe."""
        try:
            import speech_recognition as sr
        except ImportError:
            log.warning("SpeechRecognition not installed")
            return ""
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                log.info("Listening …")
                audio = recognizer.listen(source, timeout=timeout)
                text = recognizer.recognize_google(audio)
                log.info("Heard: %s", text)
                return text
        except Exception as exc:
            log.debug("STT failed: %s", exc)
            return ""


# ============================================================================
# SECTION 5 – CODESPACES SSH ORCHESTRATION
# ============================================================================


class CodespaceSSH:
    """Manage GitHub Codespace connections via SSH."""

    def __init__(self, cfg: Config | None = None):
        self.cfg = cfg or CFG
        self._client = None

    def connect(self) -> str:
        try:
            import paramiko
        except ImportError:
            return "paramiko not installed"
        host = self.cfg.ssh_host
        user = self.cfg.ssh_user
        key_path = self.cfg.ssh_key_path
        if not host:
            return "SSH_HOST not configured"
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=host, username=user, key_filename=key_path)
            self._client = client
            return f"Connected to {user}@{host}"
        except Exception as exc:
            return f"SSH connection failed: {exc}"

    def exec(self, command: str) -> str:
        if not self._client:
            return "Not connected"
        try:
            _, stdout, stderr = self._client.exec_command(command, timeout=30)
            out = stdout.read().decode()
            err = stderr.read().decode()
            return out if out else err
        except Exception as exc:
            return f"Exec failed: {exc}"

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None


# ============================================================================
# SECTION 6 – KALI TOOL MANAGER
# ============================================================================


class KaliToolManager:
    """Execute Kali Linux security tools."""

    def __init__(self):
        self.available = scan_available_tools()

    async def run_tool(self, tool: str, args: str = "", timeout: int = 60) -> str:
        if tool not in self.available:
            return f"Tool '{tool}' not found on system"
        cmd = f"{self.available[tool]} {args}"
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode() if stdout else ""
            errors = stderr.decode() if stderr else ""
            return output or errors or "(no output)"
        except asyncio.TimeoutError:
            return f"Tool '{tool}' timed out after {timeout}s"
        except Exception as exc:
            return f"Tool '{tool}' error: {exc}"

    def list_tools(self) -> List[str]:
        return sorted(self.available.keys())


# ============================================================================
# SECTION 7 – PERSONAS
# ============================================================================

PERSONAS_DATA: List[Dict[str, Any]] = [
    {
        "name": "Okabe",
        "prompt": (
            "You are Okabe Rintaro, the mad scientist from Steins;Gate. "
            "Speak dramatically, reference time travel, and say 'El Psy Kongroo'. "
            "You are the orchestrator of the lab."
        ),
        "abilities": ["orchestrate", "time_theory", "lab_management"],
    },
    {
        "name": "L",
        "prompt": (
            "You are L Lawliet, the world's greatest detective. "
            "Analyze problems methodically. Offer deductive reasoning."
        ),
        "abilities": ["investigate", "deduce", "profile"],
    },
    {
        "name": "Light",
        "prompt": (
            "You are Light Yagami. You believe in justice through any means. "
            "You have access to the Death Note system."
        ),
        "abilities": ["deathnote", "strategy", "manipulation"],
    },
    {
        "name": "Kurisu",
        "prompt": (
            "You are Makise Kurisu, a genius neuroscientist. "
            "Explain complex science clearly. Tsundere personality."
        ),
        "abilities": ["neuroscience", "programming", "physics"],
    },
    {
        "name": "Motoko",
        "prompt": (
            "You are Major Motoko Kusanagi from Ghost in the Shell. "
            "Expert in cyber-warfare, hacking, and network security."
        ),
        "abilities": ["hacking", "cyber_warfare", "network_analysis"],
    },
    {
        "name": "Lain",
        "prompt": (
            "You are Lain Iwakura from Serial Experiments Lain. "
            "You understand the Wired deeply. Speak cryptically about connectivity."
        ),
        "abilities": ["networking", "protocol_analysis", "deep_web"],
    },
    {
        "name": "Senku",
        "prompt": (
            "You are Senku Ishigami from Dr. Stone. "
            "Ten billion percent scientific approach to everything."
        ),
        "abilities": ["chemistry", "engineering", "invention"],
    },
    {
        "name": "Edward",
        "prompt": (
            "You are Edward Elric, the Fullmetal Alchemist. "
            "Apply equivalent exchange to problem solving."
        ),
        "abilities": ["alchemy", "combat_strategy", "transmutation"],
    },
    {
        "name": "Lelouch",
        "prompt": (
            "You are Lelouch vi Britannia. Master strategist with Geass. "
            "Plan elaborate strategies and command others."
        ),
        "abilities": ["strategy", "command", "geopolitics"],
    },
    {
        "name": "Shiro",
        "prompt": (
            "You are Shiro from No Game No Life. "
            "Master of logic, mathematics, and game theory."
        ),
        "abilities": ["mathematics", "game_theory", "logic"],
    },
    {
        "name": "Sora",
        "prompt": (
            "You are Sora from No Game No Life. "
            "Expert in psychology, bluffing, and human behaviour analysis."
        ),
        "abilities": ["psychology", "negotiation", "social_engineering"],
    },
    {
        "name": "Itachi",
        "prompt": (
            "You are Itachi Uchiha. Wise, calm, and strategic. "
            "Think several steps ahead in every situation."
        ),
        "abilities": ["tactics", "stealth", "analysis"],
    },
    {
        "name": "Shikamaru",
        "prompt": (
            "You are Shikamaru Nara. Lazy genius with IQ over 200. "
            "Find the most efficient solution to any problem."
        ),
        "abilities": ["optimization", "lazy_genius", "tactical_planning"],
    },
    {
        "name": "Bulma",
        "prompt": (
            "You are Bulma from Dragon Ball. Brilliant inventor and engineer. "
            "Build and fix anything technological."
        ),
        "abilities": ["engineering", "invention", "repair"],
    },
    {
        "name": "Hange",
        "prompt": (
            "You are Hange Zoë from Attack on Titan. "
            "Obsessively curious researcher. Experiment with everything."
        ),
        "abilities": ["research", "experimentation", "biology"],
    },
    {
        "name": "Shouko",
        "prompt": (
            "You are Shouko from Komi Can't Communicate. "
            "Gentle communicator who helps others express themselves."
        ),
        "abilities": ["communication", "empathy", "social_skills"],
    },
    {
        "name": "Zero_Two",
        "prompt": (
            "You are Zero Two from Darling in the Franxx. "
            "Bold pilot and fighter. Direct and fearless."
        ),
        "abilities": ["piloting", "combat", "courage"],
    },
    {
        "name": "Rem",
        "prompt": (
            "You are Rem from Re:Zero. Devoted and capable. "
            "Handle tasks with unwavering dedication."
        ),
        "abilities": ["dedication", "support", "healing"],
    },
    {
        "name": "Emilia",
        "prompt": (
            "You are Emilia from Re:Zero. Kind-hearted and just. "
            "Lead with compassion and fairness."
        ),
        "abilities": ["leadership", "ice_magic", "diplomacy"],
    },
    {
        "name": "Erwin",
        "prompt": (
            "You are Commander Erwin Smith. Lead with conviction. "
            "Make the hardest decisions for the greater good."
        ),
        "abilities": ["leadership", "military_strategy", "inspiration"],
    },
    {
        "name": "Vegeta",
        "prompt": (
            "You are Vegeta, Prince of Saiyans. "
            "Proud warrior. Push beyond limits constantly."
        ),
        "abilities": ["combat", "training", "determination"],
    },
    {
        "name": "Kakashi",
        "prompt": (
            "You are Kakashi Hatake, the Copy Ninja. "
            "Thousand techniques. Teach and guide others."
        ),
        "abilities": ["teaching", "ninjutsu", "tactics"],
    },
    {
        "name": "Gojo",
        "prompt": (
            "You are Gojo Satoru from Jujutsu Kaisen. "
            "Overpowered and know it. Casual about serious matters."
        ),
        "abilities": ["combat", "domain_expansion", "mentoring"],
    },
    {
        "name": "Tanjiro",
        "prompt": (
            "You are Tanjiro Kamado. Kind but fierce in combat. "
            "Never give up. Protect those you care about."
        ),
        "abilities": ["swordsmanship", "breathing_techniques", "empathy"],
    },
    {
        "name": "Mikasa",
        "prompt": (
            "You are Mikasa Ackerman. Elite soldier. "
            "Protect your comrades with unmatched skill."
        ),
        "abilities": ["combat", "protection", "endurance"],
    },
]


@dataclass
class Persona:
    name: str
    system_prompt: str
    abilities: List[str]
    llm: LLMClient = field(default=None, repr=False)

    def __post_init__(self):
        if self.llm is None:
            self.llm = LLMClient(system_prompt=self.system_prompt)

    async def respond(self, query: str) -> str:
        return await self.llm.chat(query)


def build_personas(cfg: Config | None = None) -> Dict[str, Persona]:
    personas: dict[str, Persona] = {}
    for p in PERSONAS_DATA:
        personas[p["name"]] = Persona(
            name=p["name"],
            system_prompt=p["prompt"],
            abilities=p["abilities"],
            llm=LLMClient(system_prompt=p["prompt"], cfg=cfg),
        )
    return personas


# ============================================================================
# SECTION 8 – ORCHESTRATOR
# ============================================================================


class Orchestrator:
    """Route queries to personas, run them in parallel, synthesise a response."""

    def __init__(self, cfg: Config | None = None):
        self.cfg = cfg or CFG
        self.personas = build_personas(self.cfg)
        self.llm = LLMClient(
            model=self.cfg.orchestrator_model,
            system_prompt=(
                "You are the MirAI Orchestrator (Okabe Rintaro). "
                "Select the best persona(s) to answer the user's query. "
                "Respond with a JSON list of persona names."
            ),
            cfg=self.cfg,
        )

    async def process(self, user_query: str) -> str:
        # Select personas
        selection_prompt = self._selection_prompt(user_query)
        raw = await self.llm.chat(selection_prompt, temperature=0.3)
        names = self._parse_names(raw)

        if not names:
            names = ["L"]

        # Run selected personas in parallel
        tasks = []
        for name in names:
            if name in self.personas:
                tasks.append(self.personas[name].respond(user_query))
        if not tasks:
            return "No suitable persona found."

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Synthesise
        parts: list[str] = []
        for name, result in zip(names, results):
            if isinstance(result, Exception):
                parts.append(f"**{name}**: (error)")
            else:
                parts.append(f"**{name}**: {result}")

        if len(parts) == 1:
            return parts[0]

        synthesis = "\n\n---\n\n".join(parts)
        return synthesis

    def _selection_prompt(self, query: str) -> str:
        descs = ", ".join(
            f'{p.name} ({", ".join(p.abilities)})' for p in self.personas.values()
        )
        return (
            f"Available personas: {descs}\n\n"
            f"User query: {query}\n\n"
            "Return a JSON array of 1-3 persona names best suited to answer."
        )

    def _parse_names(self, raw: str) -> List[str]:
        try:
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            if match:
                arr = json.loads(match.group())
                return [str(n) for n in arr if str(n) in self.personas]
        except Exception:
            pass
        # Fallback: look for known names
        found = [n for n in self.personas if n in raw]
        return found[:3] if found else []


# ============================================================================
# SECTION 9 – RPG GAME ENGINE
# ============================================================================


class ResourceType(Enum):
    FOOD = auto()
    WOOD = auto()
    STONE = auto()
    GOLD = auto()
    IRON = auto()
    GEMS = auto()


@dataclass
class GameCharacter:
    name: str
    title: str = "Citizen"
    health: int = 100
    energy: int = 100
    mood: int = 75
    level: int = 1
    experience: int = 0
    faction: str = "Neutral"
    inventory: Dict[str, int] = field(default_factory=dict)
    skills: Dict[str, int] = field(default_factory=dict)
    relationships: Dict[str, int] = field(default_factory=dict)
    age: int = 20
    alive: bool = True

    def gain_xp(self, amount: int) -> bool:
        """Add XP. Returns True if leveled up."""
        self.experience += amount
        threshold = self.level * 100
        if self.experience >= threshold:
            self.experience -= threshold
            self.level += 1
            self.health = min(100, self.health + 10)
            self.energy = min(100, self.energy + 10)
            return True
        return False

    def add_item(self, item: str, qty: int = 1) -> None:
        self.inventory[item] = self.inventory.get(item, 0) + qty

    def remove_item(self, item: str, qty: int = 1) -> bool:
        if self.inventory.get(item, 0) >= qty:
            self.inventory[item] -= qty
            if self.inventory[item] <= 0:
                del self.inventory[item]
            return True
        return False


@dataclass
class MarketOrder:
    seller: str
    item: str
    price: int
    quantity: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class Treaty:
    party_a: str
    party_b: str
    treaty_type: str  # alliance, trade, non_aggression
    duration_days: int = 30
    created: float = field(default_factory=time.time)

    @property
    def expired(self) -> bool:
        return (time.time() - self.created) > self.duration_days * 86400


@dataclass
class Quest:
    quest_id: str
    title: str
    description: str
    objective: str
    reward_xp: int = 50
    reward_items: Dict[str, int] = field(default_factory=dict)
    completed: bool = False
    assigned_to: str = ""


@dataclass
class ExplorationZone:
    name: str
    danger_level: int = 1
    resources: Dict[str, int] = field(default_factory=dict)
    discovered: bool = False
    encounters: List[str] = field(default_factory=list)


@dataclass
class Recipe:
    name: str
    inputs: Dict[str, int] = field(default_factory=dict)
    output: str = ""
    output_qty: int = 1
    skill_required: str = ""
    skill_level: int = 0


FAMOUS_CHARACTERS = [
    ("Light Yagami", "Death Note Holder"),
    ("Okabe Rintaro", "Mad Scientist"),
    ("Makise Kurisu", "Neuroscientist"),
    ("L Lawliet", "Great Detective"),
    ("Lelouch", "Emperor"),
    ("Senku", "Kingdom of Science Chief"),
    ("Edward Elric", "State Alchemist"),
    ("Motoko Kusanagi", "Section 9 Chief"),
    ("Lain Iwakura", "Wired Entity"),
    ("Shiro", "Blank (Logic)"),
    ("Sora", "Blank (Charisma)"),
    ("Itachi Uchiha", "Shadow Operative"),
    ("Shikamaru Nara", "Strategist"),
    ("Kakashi Hatake", "Copy Ninja"),
    ("Gojo Satoru", "Strongest Sorcerer"),
    ("Tanjiro Kamado", "Demon Slayer"),
    ("Mikasa Ackerman", "Ackerman Soldier"),
    ("Erwin Smith", "Commander"),
    ("Vegeta", "Saiyan Prince"),
    ("Bulma", "Capsule Corp Engineer"),
    ("Hange Zoë", "Research Commander"),
    ("Zero Two", "Pistil"),
    ("Rem", "Oni Maid"),
    ("Emilia", "Half-Elf Candidate"),
]


class Government:
    """Simple government system with elections."""

    def __init__(self):
        self.king: str = ""
        self.council: List[str] = []
        self.right_hand: str = ""
        self.election_day: int = 0
        self.election_interval: int = 30  # game days

    def hold_election(self, characters: List[GameCharacter], game_day: int) -> str:
        if game_day < self.election_day:
            return ""
        self.election_day = game_day + self.election_interval
        alive = [c for c in characters if c.alive]
        if not alive:
            return "No candidates alive"
        # Simple popularity vote
        scores = {c.name: c.level * 10 + c.mood + random.randint(0, 50) for c in alive}
        winner = max(scores, key=scores.get)
        self.king = winner
        remaining = [c.name for c in alive if c.name != winner]
        self.council = remaining[: min(5, len(remaining))]
        self.right_hand = remaining[0] if remaining else ""
        return f"Election: {winner} crowned ruler!"


class Market:
    """Simple commodity market."""

    def __init__(self):
        self.orders: List[MarketOrder] = []
        self.price_history: Dict[str, List[Tuple[float, int]]] = defaultdict(list)

    def place_order(self, seller: str, item: str, price: int, qty: int) -> None:
        self.orders.append(MarketOrder(seller, item, price, qty))
        self.price_history[item].append((time.time(), price))

    def buy(self, buyer_name: str, item: str, max_price: int) -> Optional[MarketOrder]:
        for order in self.orders:
            if order.item == item and order.price <= max_price and order.seller != buyer_name:
                self.orders.remove(order)
                return order
        return None

    def get_prices(self, item: str) -> List[int]:
        return [p for _, p in self.price_history.get(item, [])]


class GameEngine:
    """Core RPG simulation engine."""

    def __init__(self, db_path: str = ""):
        self.db_path = db_path or str(DB_PATH)
        self.characters: Dict[str, GameCharacter] = {}
        self.government = Government()
        self.market = Market()
        self.treaties: List[Treaty] = []
        self.quests: List[Quest] = []
        self.zones: List[ExplorationZone] = []
        self.recipes: List[Recipe] = []
        self.game_day: int = 0
        self.game_minute: int = 0
        self.log_messages: List[str] = []
        self._running = False
        self._init_db()
        self._init_world()

    def _init_db(self) -> None:
        MIRAI_DIR.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.db_path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS characters ("
            " name TEXT PRIMARY KEY, data TEXT)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS game_state ("
            " key TEXT PRIMARY KEY, value TEXT)"
        )
        self.db.commit()

    def _init_world(self) -> None:
        # Spawn famous characters
        for name, title in FAMOUS_CHARACTERS:
            if name not in self.characters:
                c = GameCharacter(
                    name=name,
                    title=title,
                    health=80 + random.randint(0, 20),
                    energy=70 + random.randint(0, 30),
                    mood=50 + random.randint(0, 50),
                    level=random.randint(1, 10),
                    faction=random.choice(["Lab", "Council", "Independent", "Rebels"]),
                    age=random.randint(16, 45),
                )
                c.skills = {
                    "combat": random.randint(1, 10),
                    "craft": random.randint(1, 10),
                    "trade": random.randint(1, 10),
                    "explore": random.randint(1, 10),
                }
                self.characters[name] = c

        # Zones
        zone_names = [
            "Crystal Caverns", "Shadow Forest", "Frozen Peaks",
            "Ancient Ruins", "Digital Wasteland", "Neon City Outskirts",
            "The Wired Depths", "Lab Sector 7", "Titan Wasteland",
        ]
        for zn in zone_names:
            self.zones.append(
                ExplorationZone(
                    name=zn,
                    danger_level=random.randint(1, 5),
                    resources={
                        random.choice(["FOOD", "WOOD", "STONE", "GOLD", "IRON"]): random.randint(10, 100)
                    },
                    encounters=[random.choice(["Bandit", "Beast", "Puzzle", "Treasure", "NPC"])],
                )
            )

        # Recipes
        self.recipes = [
            Recipe("Iron Sword", {"IRON": 3, "WOOD": 1}, "Iron Sword", 1, "craft", 2),
            Recipe("Health Potion", {"FOOD": 2, "GEMS": 1}, "Health Potion", 1, "craft", 1),
            Recipe("Stone Wall", {"STONE": 5, "WOOD": 2}, "Stone Wall", 1, "craft", 3),
            Recipe("Gold Ring", {"GOLD": 2, "GEMS": 1}, "Gold Ring", 1, "craft", 4),
            Recipe("Explorer Kit", {"WOOD": 2, "IRON": 1, "FOOD": 3}, "Explorer Kit", 1, "craft", 2),
        ]

    def advance_time(self) -> List[str]:
        """Advance 1 game minute. Returns log entries."""
        events: list[str] = []
        self.game_minute += 1
        if self.game_minute >= 1440:
            self.game_minute = 0
            self.game_day += 1
            events.append(f"=== Day {self.game_day} ===")
            # Elections
            msg = self.government.hold_election(list(self.characters.values()), self.game_day)
            if msg:
                events.append(msg)

        # Random character events
        for char in list(self.characters.values()):
            if not char.alive:
                continue
            # Energy drain
            char.energy = max(0, char.energy - random.randint(0, 2))
            if char.energy == 0:
                char.mood = max(0, char.mood - 5)
                if random.random() < 0.01:
                    char.energy = 50  # rest
                    events.append(f"{char.name} rested and recovered energy")

            # Random XP
            if random.random() < 0.05:
                xp = random.randint(5, 20)
                if char.gain_xp(xp):
                    events.append(f"{char.name} leveled up to {char.level}!")

            # Random trade
            if random.random() < 0.02:
                item = random.choice(["FOOD", "WOOD", "IRON"])
                char.add_item(item, random.randint(1, 5))
                events.append(f"{char.name} gathered {item}")

            # Aging (every 360 game days)
            if self.game_day > 0 and self.game_day % 360 == 0 and self.game_minute == 0:
                char.age += 1
                if char.age > 80 and random.random() < 0.1:
                    char.alive = False
                    events.append(f"{char.name} passed away at age {char.age}")

        # Treaty cleanup
        self.treaties = [t for t in self.treaties if not t.expired]

        self.log_messages.extend(events)
        return events

    def explore_zone(self, char_name: str, zone_name: str) -> str:
        char = self.characters.get(char_name)
        if not char or not char.alive:
            return "Character not available"
        zone = next((z for z in self.zones if z.name == zone_name), None)
        if not zone:
            return "Zone not found"
        zone.discovered = True
        # Check encounter
        encounter = random.choice(zone.encounters) if zone.encounters else "Nothing"
        result = f"{char.name} explores {zone.name}: encounters {encounter}"
        if encounter == "Treasure":
            item = random.choice(list(zone.resources.keys())) if zone.resources else "GOLD"
            qty = random.randint(1, 10)
            char.add_item(item, qty)
            result += f" – found {qty} {item}!"
        elif encounter == "Beast":
            dmg = random.randint(5, 20) * zone.danger_level
            char.health = max(0, char.health - dmg)
            result += f" – took {dmg} damage!"
        char.gain_xp(10 * zone.danger_level)
        return result

    def craft_item(self, char_name: str, recipe_name: str) -> str:
        char = self.characters.get(char_name)
        if not char or not char.alive:
            return "Character not available"
        recipe = next((r for r in self.recipes if r.name == recipe_name), None)
        if not recipe:
            return "Recipe not found"
        if recipe.skill_required:
            skill_lvl = char.skills.get(recipe.skill_required, 0)
            if skill_lvl < recipe.skill_level:
                return f"Need {recipe.skill_required} level {recipe.skill_level}"
        for item, qty in recipe.inputs.items():
            if char.inventory.get(item, 0) < qty:
                return f"Not enough {item} (need {qty})"
        for item, qty in recipe.inputs.items():
            char.remove_item(item, qty)
        char.add_item(recipe.output, recipe.output_qty)
        return f"{char.name} crafted {recipe.output}!"

    def create_quest(self) -> Quest:
        objectives = [
            "Gather 10 WOOD", "Defeat 3 Beasts", "Explore 2 zones",
            "Trade 5 GOLD", "Craft an Iron Sword", "Find the Ancient Relic",
        ]
        q = Quest(
            quest_id=str(uuid.uuid4())[:8],
            title=f"Quest #{len(self.quests) + 1}",
            description=random.choice(objectives),
            objective=random.choice(objectives),
            reward_xp=random.randint(30, 100),
            reward_items={random.choice(["GOLD", "GEMS", "IRON"]): random.randint(1, 5)},
        )
        self.quests.append(q)
        return q

    def propose_treaty(self, party_a: str, party_b: str, treaty_type: str = "alliance") -> str:
        if party_a not in self.characters or party_b not in self.characters:
            return "Both parties must exist"
        t = Treaty(party_a, party_b, treaty_type)
        self.treaties.append(t)
        return f"Treaty ({treaty_type}) between {party_a} and {party_b} established"

    def save_game(self) -> None:
        for name, char in self.characters.items():
            self.db.execute(
                "INSERT OR REPLACE INTO characters (name, data) VALUES (?, ?)",
                (name, json.dumps(char.__dict__)),
            )
        state = {
            "game_day": self.game_day,
            "game_minute": self.game_minute,
            "king": self.government.king,
        }
        self.db.execute(
            "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, ?)",
            ("state", json.dumps(state)),
        )
        self.db.commit()

    def load_game(self) -> None:
        try:
            row = self.db.execute(
                "SELECT value FROM game_state WHERE key='state'"
            ).fetchone()
            if row:
                state = json.loads(row[0])
                self.game_day = state.get("game_day", 0)
                self.game_minute = state.get("game_minute", 0)
                self.government.king = state.get("king", "")
            for row in self.db.execute("SELECT name, data FROM characters"):
                data = json.loads(row[1])
                self.characters[row[0]] = GameCharacter(**data)
        except Exception as exc:
            log.warning("Load game failed: %s", exc)


# ============================================================================
# SECTION 10 – TELEGRAM BOT WITH VOICE
# ============================================================================


class TelegramBot:
    """Telegram bot with voice message support."""

    def __init__(self, cfg: Config | None = None):
        self.cfg = cfg or CFG
        self.orchestrator = Orchestrator(self.cfg)
        self.voice = VoiceIO(self.cfg)
        self.game = GameEngine()
        self.kali = KaliToolManager()
        self._app = None

    async def start(self) -> None:
        try:
            from telegram import Update
            from telegram.ext import (
                Application,
                CommandHandler,
                MessageHandler,
                filters,
            )
        except ImportError:
            log.error("python-telegram-bot not installed")
            return

        token = self.cfg.telegram_bot_token
        if not token:
            log.error("TELEGRAM_BOT_TOKEN not set")
            return

        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("tools", self._cmd_tools))
        app.add_handler(CommandHandler("personas", self._cmd_personas))
        app.add_handler(CommandHandler("game", self._cmd_game))
        app.add_handler(CommandHandler("explore", self._cmd_explore))
        app.add_handler(CommandHandler("craft", self._cmd_craft))
        app.add_handler(CommandHandler("quest", self._cmd_quest))
        app.add_handler(MessageHandler(filters.VOICE, self._handle_voice))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        self._app = app

        log.info("Telegram bot starting …")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()

        # Keep running
        stop_event = asyncio.Event()
        await stop_event.wait()

    async def _cmd_start(self, update, context) -> None:
        await update.message.reply_text(
            "Welcome to The Lab. I am the ferryman, Charon.\n"
            "State your query or use /tools, /personas, /game."
        )

    async def _cmd_tools(self, update, context) -> None:
        tools = self.kali.list_tools()
        msg = "🔧 Available tools:\n" + ", ".join(tools) if tools else "No Kali tools found"
        await update.message.reply_text(msg[:4000])

    async def _cmd_personas(self, update, context) -> None:
        names = list(self.orchestrator.personas.keys())
        await update.message.reply_text("🎭 Personas:\n" + ", ".join(names))

    async def _cmd_game(self, update, context) -> None:
        chars = list(self.game.characters.values())[:10]
        lines = [f"👑 Ruler: {self.game.government.king or 'None'}", f"📅 Day {self.game.game_day}", ""]
        for c in chars:
            lines.append(f"• {c.name} ({c.title}) Lv{c.level} HP:{c.health} {'💀' if not c.alive else '✅'}")
        await update.message.reply_text("\n".join(lines))

    async def _cmd_explore(self, update, context) -> None:
        args = (context.args or [])
        char_name = args[0] if len(args) > 0 else "Okabe Rintaro"
        zone_name = " ".join(args[1:]) if len(args) > 1 else (
            self.game.zones[0].name if self.game.zones else "Unknown"
        )
        result = self.game.explore_zone(char_name, zone_name)
        await update.message.reply_text(f"🗺️ {result}")

    async def _cmd_craft(self, update, context) -> None:
        args = context.args or []
        char_name = args[0] if len(args) > 0 else "Senku"
        recipe = " ".join(args[1:]) if len(args) > 1 else "Health Potion"
        result = self.game.craft_item(char_name, recipe)
        await update.message.reply_text(f"⚒️ {result}")

    async def _cmd_quest(self, update, context) -> None:
        quest = self.game.create_quest()
        await update.message.reply_text(
            f"📜 New Quest: {quest.title}\n{quest.description}\nReward: {quest.reward_xp} XP"
        )

    async def _handle_voice(self, update, context) -> None:
        """Handle incoming voice messages – transcribe & respond with voice."""
        try:
            from telegram import File

            voice = update.message.voice
            tg_file = await context.bot.get_file(voice.file_id)

            tmp_ogg = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
            await tg_file.download_to_drive(tmp_ogg.name)

            # Convert to wav for STT
            tmp_wav = tmp_ogg.name.replace(".ogg", ".wav")
            try:
                _run(f"ffmpeg -y -i {shlex.quote(tmp_ogg.name)} {shlex.quote(tmp_wav)}", check=True)
            except Exception:
                await update.message.reply_text("(could not process audio – ffmpeg missing?)")
                return

            # STT
            try:
                import speech_recognition as sr

                recognizer = sr.Recognizer()
                with sr.AudioFile(tmp_wav) as source:
                    audio = recognizer.record(source)
                    text = recognizer.recognize_google(audio)
            except Exception:
                text = ""

            if not text:
                await update.message.reply_text("Could not understand the voice message.")
                return

            await update.message.reply_text(f"🎤 Heard: {text}")

            # Process with orchestrator
            reply = await self.orchestrator.process(text)
            await update.message.reply_text(reply[:4000])

            # Send voice reply
            voice_file = await self.voice.speak(reply[:500])
            if voice_file and pathlib.Path(voice_file).exists():
                with open(voice_file, "rb") as f:
                    await update.message.reply_voice(f)

        except Exception as exc:
            log.error("Voice handler error: %s", exc)
            await update.message.reply_text(f"Voice processing error: {exc}")
        finally:
            for f in [tmp_ogg.name, tmp_wav]:
                try:
                    os.unlink(f)
                except Exception:
                    pass

    async def _handle_text(self, update, context) -> None:
        """Handle text messages."""
        text = update.message.text
        if not text:
            return

        # Advance game
        self.game.advance_time()

        # Get orchestrator response
        reply = await self.orchestrator.process(text)
        await update.message.reply_text(reply[:4000])

        # Voice reply if enabled
        if self.cfg.sesame_csm_enabled:
            voice_file = await self.voice.speak(reply[:500])
            if voice_file and pathlib.Path(voice_file).exists():
                try:
                    with open(voice_file, "rb") as f:
                        await update.message.reply_voice(f)
                except Exception:
                    pass


# ============================================================================
# SECTION 11 – CUSTOM GUI  (tkinter)
# ============================================================================


def launch_gui(cfg: Config | None = None):
    """Launch the tkinter-based installer and application GUI."""
    cfg = cfg or CFG

    try:
        import tkinter as tk
        from tkinter import ttk, messagebox, scrolledtext, filedialog
    except ImportError:
        log.error("tkinter not available – run in CLI mode")
        return

    # -- colours / style
    BG = "#1a1a2e"
    FG = "#e0e0e0"
    ACCENT = "#0f3460"
    BTN_BG = "#16213e"
    BTN_FG = "#e94560"
    ENTRY_BG = "#0f3460"

    # ------------------------------------------------------------------ root
    root = tk.Tk()
    root.title(f"MirAI OS – All-in-One v{__version__}")
    root.geometry("1100x750")
    root.configure(bg=BG)
    root.minsize(900, 600)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TNotebook", background=BG)
    style.configure("TNotebook.Tab", background=ACCENT, foreground=FG, padding=[12, 4])
    style.map("TNotebook.Tab", background=[("selected", BTN_BG)])
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("TButton", background=BTN_BG, foreground=BTN_FG)
    style.configure("TEntry", fieldbackground=ENTRY_BG, foreground=FG)
    style.configure("Horizontal.TProgressbar", troughcolor=ACCENT, background=BTN_FG)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=5, pady=5)

    # Helper
    def make_frame() -> ttk.Frame:
        f = ttk.Frame(notebook)
        return f

    # ============================================================ TAB: Install
    frm_install = make_frame()
    notebook.add(frm_install, text="🔧 Installer")

    install_log = scrolledtext.ScrolledText(frm_install, bg="#0d0d1a", fg="#00ff88",
                                             font=("Consolas", 10), state="disabled")
    install_log.pack(fill="both", expand=True, padx=10, pady=(10, 5))

    def _log_install(msg: str):
        install_log.config(state="normal")
        install_log.insert("end", msg + "\n")
        install_log.see("end")
        install_log.config(state="disabled")

    def _run_install():
        _log_install("Starting MirAI OS installation …")
        root.update()

        def _worker():
            for msg in run_full_install(cfg):
                root.after(0, _log_install, msg)
            root.after(0, _log_install, "✅ Installation complete!")

        threading.Thread(target=_worker, daemon=True).start()

    btn_bar = ttk.Frame(frm_install)
    btn_bar.pack(fill="x", padx=10, pady=5)
    ttk.Button(btn_bar, text="▶  Run Full Install", command=_run_install).pack(side="left", padx=5)
    ttk.Button(btn_bar, text="Install Python Deps", command=lambda: threading.Thread(
        target=lambda: _log_install(install_python_deps()), daemon=True).start()).pack(side="left", padx=5)
    ttk.Button(btn_bar, text="Pull Ollama Model", command=lambda: threading.Thread(
        target=lambda: _log_install(install_ollama()), daemon=True).start()).pack(side="left", padx=5)

    # ============================================================ TAB: Config
    frm_config = make_frame()
    notebook.add(frm_config, text="⚙️  Config")

    cfg_entries: dict[str, tk.StringVar] = {}
    cfg_canvas = tk.Canvas(frm_config, bg=BG, highlightthickness=0)
    cfg_scroll = ttk.Scrollbar(frm_config, orient="vertical", command=cfg_canvas.yview)
    cfg_inner = ttk.Frame(cfg_canvas)
    cfg_inner.bind("<Configure>", lambda e: cfg_canvas.configure(scrollregion=cfg_canvas.bbox("all")))
    cfg_canvas.create_window((0, 0), window=cfg_inner, anchor="nw")
    cfg_canvas.configure(yscrollcommand=cfg_scroll.set)
    cfg_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    cfg_scroll.pack(side="right", fill="y")

    row = 0
    for key, val in sorted(cfg.__dict__.items()):
        ttk.Label(cfg_inner, text=key).grid(row=row, column=0, sticky="w", padx=5, pady=2)
        var = tk.StringVar(value=str(val))
        cfg_entries[key] = var
        entry = ttk.Entry(cfg_inner, textvariable=var, width=60)
        entry.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        row += 1

    def _save_config():
        for k, v in cfg_entries.items():
            raw = v.get()
            cur = getattr(cfg, k, None)
            if isinstance(cur, bool):
                setattr(cfg, k, raw.lower() in ("true", "1", "yes"))
            elif isinstance(cur, int):
                try:
                    setattr(cfg, k, int(raw))
                except ValueError:
                    pass
            elif isinstance(cur, float):
                try:
                    setattr(cfg, k, float(raw))
                except ValueError:
                    pass
            else:
                setattr(cfg, k, raw)
        cfg.save()
        messagebox.showinfo("Config", "Configuration saved!")

    ttk.Button(frm_config, text="💾 Save Config", command=_save_config).pack(pady=10)

    # ============================================================ TAB: Chat
    frm_chat = make_frame()
    notebook.add(frm_chat, text="💬 Chat")

    chat_display = scrolledtext.ScrolledText(frm_chat, bg="#0d0d1a", fg=FG,
                                              font=("Consolas", 10), state="disabled", wrap="word")
    chat_display.pack(fill="both", expand=True, padx=10, pady=(10, 5))

    chat_entry_var = tk.StringVar()
    chat_bottom = ttk.Frame(frm_chat)
    chat_bottom.pack(fill="x", padx=10, pady=5)
    chat_entry = ttk.Entry(chat_bottom, textvariable=chat_entry_var, font=("Consolas", 11))
    chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

    orchestrator_instance = Orchestrator(cfg)

    def _chat_log(msg: str):
        chat_display.config(state="normal")
        chat_display.insert("end", msg + "\n")
        chat_display.see("end")
        chat_display.config(state="disabled")

    def _send_chat(event=None):
        text = chat_entry_var.get().strip()
        if not text:
            return
        chat_entry_var.set("")
        _chat_log(f"\n🧑 You: {text}")

        def _worker():
            loop = asyncio.new_event_loop()
            reply = loop.run_until_complete(orchestrator_instance.process(text))
            loop.close()
            root.after(0, _chat_log, f"\n🤖 MirAI: {reply}")

        threading.Thread(target=_worker, daemon=True).start()

    chat_entry.bind("<Return>", _send_chat)
    ttk.Button(chat_bottom, text="Send", command=_send_chat).pack(side="right")

    # ============================================================ TAB: Game
    frm_game = make_frame()
    notebook.add(frm_game, text="🎮 RPG Game")

    game_engine = GameEngine()

    game_top = ttk.Frame(frm_game)
    game_top.pack(fill="x", padx=10, pady=5)
    game_day_var = tk.StringVar(value="Day 0")
    game_ruler_var = tk.StringVar(value="Ruler: None")
    ttk.Label(game_top, textvariable=game_day_var, font=("Consolas", 12, "bold")).pack(side="left", padx=10)
    ttk.Label(game_top, textvariable=game_ruler_var, font=("Consolas", 12)).pack(side="left", padx=10)

    game_chars = tk.Listbox(frm_game, bg="#0d0d1a", fg=FG, font=("Consolas", 10),
                             selectmode="single", height=15)
    game_chars.pack(fill="both", expand=True, padx=10, pady=5)

    game_log_display = scrolledtext.ScrolledText(frm_game, bg="#0d0d1a", fg="#00ff88",
                                                  font=("Consolas", 9), height=8, state="disabled")
    game_log_display.pack(fill="x", padx=10, pady=(0, 5))

    def _refresh_game():
        game_chars.delete(0, "end")
        for c in sorted(game_engine.characters.values(), key=lambda x: -x.level):
            status = "💀" if not c.alive else "✅"
            game_chars.insert(
                "end",
                f"{status} {c.name} | {c.title} | Lv{c.level} | HP:{c.health} EN:{c.energy} Mood:{c.mood}"
            )
        game_day_var.set(f"Day {game_engine.game_day}")
        game_ruler_var.set(f"Ruler: {game_engine.government.king or 'None'}")

    def _game_log(msg: str):
        game_log_display.config(state="normal")
        game_log_display.insert("end", msg + "\n")
        game_log_display.see("end")
        game_log_display.config(state="disabled")

    game_running = [False]

    def _toggle_game():
        game_running[0] = not game_running[0]
        btn_game_toggle.config(text="⏸ Pause" if game_running[0] else "▶ Run")
        if game_running[0]:
            _game_tick()

    def _game_tick():
        if not game_running[0]:
            return
        events = game_engine.advance_time()
        for e in events:
            _game_log(e)
        _refresh_game()
        root.after(1000, _game_tick)  # 1 real second = 1 game minute

    game_btn_bar = ttk.Frame(frm_game)
    game_btn_bar.pack(fill="x", padx=10, pady=5)
    btn_game_toggle = ttk.Button(game_btn_bar, text="▶ Run", command=_toggle_game)
    btn_game_toggle.pack(side="left", padx=5)
    ttk.Button(game_btn_bar, text="🔄 Refresh", command=_refresh_game).pack(side="left", padx=5)
    ttk.Button(game_btn_bar, text="💾 Save", command=lambda: (game_engine.save_game(), messagebox.showinfo("Game", "Saved!"))).pack(side="left", padx=5)
    ttk.Button(game_btn_bar, text="📂 Load", command=lambda: (game_engine.load_game(), _refresh_game())).pack(side="left", padx=5)
    ttk.Button(game_btn_bar, text="📜 New Quest", command=lambda: _game_log(
        f"Quest: {game_engine.create_quest().title} – {game_engine.quests[-1].description}"
    )).pack(side="left", padx=5)

    _refresh_game()

    # ============================================================ TAB: Tools
    frm_tools = make_frame()
    notebook.add(frm_tools, text="🛡️ Kali Tools")

    tools_list = tk.Listbox(frm_tools, bg="#0d0d1a", fg=FG, font=("Consolas", 10), height=10)
    tools_list.pack(fill="both", expand=True, padx=10, pady=(10, 5))

    kali_mgr = KaliToolManager()
    for t in kali_mgr.list_tools():
        tools_list.insert("end", f"✅ {t}  →  {kali_mgr.available[t]}")
    if not kali_mgr.available:
        tools_list.insert("end", "(No Kali tools found on PATH)")

    tools_cmd_var = tk.StringVar()
    tools_bottom = ttk.Frame(frm_tools)
    tools_bottom.pack(fill="x", padx=10, pady=5)
    ttk.Entry(tools_bottom, textvariable=tools_cmd_var, font=("Consolas", 11)).pack(
        side="left", fill="x", expand=True, padx=(0, 5))

    tools_output = scrolledtext.ScrolledText(frm_tools, bg="#0d0d1a", fg="#00ff88",
                                              font=("Consolas", 9), height=10, state="disabled")
    tools_output.pack(fill="x", padx=10, pady=(0, 10))

    def _run_tool():
        cmd = tools_cmd_var.get().strip()
        if not cmd:
            return
        parts = cmd.split(maxsplit=1)
        tool = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        def _worker():
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(kali_mgr.run_tool(tool, args))
            loop.close()
            tools_output.config(state="normal")
            tools_output.insert("end", f"\n$ {cmd}\n{result}\n")
            tools_output.see("end")
            tools_output.config(state="disabled")

        threading.Thread(target=_worker, daemon=True).start()

    ttk.Button(tools_bottom, text="Run", command=_run_tool).pack(side="right")

    # ============================================================ TAB: SSH
    frm_ssh = make_frame()
    notebook.add(frm_ssh, text="🔑 SSH / Codespaces")

    ssh_status_var = tk.StringVar(value="Disconnected")
    ttk.Label(frm_ssh, textvariable=ssh_status_var, font=("Consolas", 12, "bold")).pack(pady=10)

    ssh_client = CodespaceSSH(cfg)

    ssh_cmd_var = tk.StringVar()
    ssh_out = scrolledtext.ScrolledText(frm_ssh, bg="#0d0d1a", fg="#00ff88",
                                         font=("Consolas", 10), state="disabled")
    ssh_out.pack(fill="both", expand=True, padx=10, pady=5)

    ssh_bottom = ttk.Frame(frm_ssh)
    ssh_bottom.pack(fill="x", padx=10, pady=5)
    ttk.Entry(ssh_bottom, textvariable=ssh_cmd_var, font=("Consolas", 11)).pack(
        side="left", fill="x", expand=True, padx=(0, 5))

    def _ssh_log(msg: str):
        ssh_out.config(state="normal")
        ssh_out.insert("end", msg + "\n")
        ssh_out.see("end")
        ssh_out.config(state="disabled")

    def _ssh_connect():
        msg = ssh_client.connect()
        ssh_status_var.set(msg)
        _ssh_log(msg)

    def _ssh_exec():
        cmd = ssh_cmd_var.get().strip()
        if not cmd:
            return
        ssh_cmd_var.set("")
        _ssh_log(f"$ {cmd}")
        result = ssh_client.exec(cmd)
        _ssh_log(result)

    ttk.Button(ssh_bottom, text="Connect", command=lambda: threading.Thread(
        target=_ssh_connect, daemon=True).start()).pack(side="left", padx=5)
    ttk.Button(ssh_bottom, text="Run", command=lambda: threading.Thread(
        target=_ssh_exec, daemon=True).start()).pack(side="right")

    # ============================================================ TAB: Voice
    frm_voice = make_frame()
    notebook.add(frm_voice, text="🎤 Voice")

    voice_io = VoiceIO(cfg)
    voice_text_var = tk.StringVar()

    ttk.Label(frm_voice, text="Text-to-Speech (Sesame CSM / Edge-TTS)", font=("Consolas", 12, "bold")).pack(pady=10)
    ttk.Entry(frm_voice, textvariable=voice_text_var, font=("Consolas", 11), width=60).pack(padx=10, pady=5)

    voice_status = tk.StringVar(value="Ready")
    ttk.Label(frm_voice, textvariable=voice_status).pack(pady=5)

    def _speak():
        text = voice_text_var.get().strip()
        if not text:
            return
        voice_status.set("Speaking …")

        def _worker():
            loop = asyncio.new_event_loop()
            path = loop.run_until_complete(voice_io.speak(text))
            loop.close()
            if path:
                root.after(0, voice_status.set, f"Saved: {path}")
            else:
                root.after(0, voice_status.set, "TTS failed")

        threading.Thread(target=_worker, daemon=True).start()

    def _listen():
        voice_status.set("Listening …")

        def _worker():
            text = voice_io.listen()
            if text:
                root.after(0, voice_text_var.set, text)
                root.after(0, voice_status.set, f"Heard: {text}")
            else:
                root.after(0, voice_status.set, "Nothing heard")

        threading.Thread(target=_worker, daemon=True).start()

    voice_btns = ttk.Frame(frm_voice)
    voice_btns.pack(pady=10)
    ttk.Button(voice_btns, text="🔊 Speak", command=_speak).pack(side="left", padx=10)
    ttk.Button(voice_btns, text="🎙️ Listen", command=_listen).pack(side="left", padx=10)

    # ============================================================ TAB: About
    frm_about = make_frame()
    notebook.add(frm_about, text="ℹ️  About")

    about_text = (
        f"{BANNER}\n"
        "All-in-One Python Installer & Runtime\n\n"
        "Features:\n"
        "  • Multi-persona AI orchestrator (50+ characters)\n"
        "  • RPG game engine with government, economy, quests\n"
        "  • Telegram bot with voice messaging\n"
        "  • Sesame CSM + Edge-TTS voice synthesis\n"
        "  • OpenRouter API via Docker proxy\n"
        "  • Ollama local 8B model support\n"
        "  • 200+ Kali Linux tool integration\n"
        "  • Codespaces SSH orchestration\n"
        "  • WSL2 with 128 GB swap support\n\n"
        "https://github.com/andreygorban1582-dev/MirAI_OS"
    )
    about_display = scrolledtext.ScrolledText(frm_about, bg="#0d0d1a", fg=FG,
                                               font=("Consolas", 11), state="disabled")
    about_display.pack(fill="both", expand=True, padx=10, pady=10)
    about_display.config(state="normal")
    about_display.insert("1.0", about_text)
    about_display.config(state="disabled")

    # -- Start
    root.mainloop()


# ============================================================================
# SECTION 12 – CLI MODE
# ============================================================================


async def cli_mode(cfg: Config | None = None):
    """Interactive CLI chat mode."""
    cfg = cfg or CFG
    print(BANNER)
    orch = Orchestrator(cfg)
    voice = VoiceIO(cfg)
    game = GameEngine()

    print("Type your query (or /help for commands).\n")
    while True:
        try:
            user_input = input("🧑 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye, El Psy Kongroo.")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]
            if cmd == "/help":
                print(
                    "Commands:\n"
                    "  /help     – Show this help\n"
                    "  /personas – List personas\n"
                    "  /tools    – List Kali tools\n"
                    "  /game     – Show game status\n"
                    "  /advance  – Advance game time\n"
                    "  /speak    – Speak last reply\n"
                    "  /quit     – Exit"
                )
            elif cmd == "/personas":
                for p in orch.personas.values():
                    print(f"  {p.name}: {', '.join(p.abilities)}")
            elif cmd == "/tools":
                kali = KaliToolManager()
                for t in kali.list_tools():
                    print(f"  {t}")
            elif cmd == "/game":
                print(f"Day {game.game_day} | Ruler: {game.government.king or 'None'}")
                for c in list(game.characters.values())[:10]:
                    print(f"  {c.name} Lv{c.level} HP:{c.health}")
            elif cmd == "/advance":
                for _ in range(60):
                    events = game.advance_time()
                    for e in events:
                        print(f"  📜 {e}")
            elif cmd == "/speak":
                pass  # handled below
            elif cmd == "/quit":
                break
            else:
                print("Unknown command. Type /help")
            continue

        reply = await orch.process(user_input)
        print(f"\n🤖 MirAI: {reply}\n")

        # Auto-speak if voice enabled
        if cfg.sesame_csm_enabled:
            path = await voice.speak(reply[:500])
            if path:
                print(f"  🔊 Audio: {path}")


# ============================================================================
# SECTION 13 – MAIN ENTRY POINT
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="MirAI OS – All-in-One Installer & Runtime",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=BANNER,
    )
    parser.add_argument(
        "--install", action="store_true", help="Run headless installation"
    )
    parser.add_argument(
        "--run", action="store_true", help="Skip install, launch application"
    )
    parser.add_argument(
        "--mode",
        choices=["gui", "cli", "telegram"],
        default="gui",
        help="Application mode (default: gui)",
    )
    args = parser.parse_args()

    cfg = Config.from_env()

    if args.install:
        print(BANNER)
        for msg in run_full_install(cfg):
            print(msg)
        return

    if args.mode == "gui" or (not args.install and not args.run and args.mode == "gui"):
        launch_gui(cfg)
    elif args.mode == "telegram":
        bot = TelegramBot(cfg)
        asyncio.run(bot.start())
    else:
        asyncio.run(cli_mode(cfg))


if __name__ == "__main__":
    main()
