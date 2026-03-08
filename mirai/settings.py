"""
mirai/settings.py
─────────────────
Centralised settings loader.
═════════════════════════════════════════════════════════════════════════════
What this module does
─────────────────────
• Reads config/config.yaml for structured defaults.
• Reads .env (if present) for secrets / overrides via python-dotenv.
• Exposes a single `settings` singleton used everywhere in the package.

This two-layer approach means:
  – You can keep non-secret settings in YAML (version-controlled).
  – Secrets stay in .env (git-ignored).
  – Environment variables always win over both (useful in CI/CD).
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from loguru import logger

# ── Locate project root ────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT / ".env"
_CONFIG_FILE = _ROOT / "config" / "config.yaml"

# Load .env if it exists (does nothing if not found)
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)
else:
    logger.warning(
        f".env file not found at {_ENV_FILE}. "
        "Copy .env.example → .env and fill in your secrets."
    )


def _load_yaml() -> dict:
    if _CONFIG_FILE.exists():
        with open(_CONFIG_FILE, "r") as f:
            return yaml.safe_load(f) or {}
    logger.warning(f"config.yaml not found at {_CONFIG_FILE}")
    return {}


class _Settings:
    """
    Lazily reads config.yaml + environment variables.

    All attributes are resolved at first access so the class can be imported
    before .env is loaded in some edge-cases.
    """

    def __init__(self) -> None:
        self._cfg: dict = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._cfg = _load_yaml()
            self._loaded = True

    def _yaml(self, *keys: str, default=None):
        """Drill into nested YAML keys, e.g. _yaml('llm','temperature')."""
        self._ensure_loaded()
        node = self._cfg
        for k in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(k, default)
        return node

    # ── OpenRouter ────────────────────────────────────────────────────────────
    @property
    def openrouter_api_key(self) -> str:
        return os.getenv("OPENROUTER_API_KEY", "")

    @property
    def openrouter_model(self) -> str:
        return os.getenv(
            "OPENROUTER_MODEL",
            self._yaml("llm", "model", default="openai/gpt-4o"),
        )

    @property
    def openrouter_base_url(self) -> str:
        return os.getenv(
            "OPENROUTER_BASE_URL",
            self._yaml("llm", "base_url", default="https://openrouter.ai/api/v1"),
        )

    @property
    def llm_system_prompt(self) -> str:
        return self._yaml("llm", "system_prompt", default="You are MirAI, a helpful AI.")

    @property
    def llm_temperature(self) -> float:
        return float(
            os.getenv("LLM_TEMPERATURE", str(self._yaml("llm", "temperature", default=0.85)))
        )

    @property
    def llm_max_tokens(self) -> int:
        return int(
            os.getenv("LLM_MAX_TOKENS", str(self._yaml("llm", "max_tokens", default=4096)))
        )

    # ── Telegram ──────────────────────────────────────────────────────────────
    @property
    def telegram_token(self) -> str:
        return os.getenv("TELEGRAM_BOT_TOKEN", "")

    @property
    def telegram_allowed_users(self) -> list[int]:
        raw = os.getenv("TELEGRAM_ALLOWED_USERS", "")
        if not raw.strip():
            return []
        return [int(uid.strip()) for uid in raw.split(",") if uid.strip().isdigit()]

    # ── GitHub ────────────────────────────────────────────────────────────────
    @property
    def github_token(self) -> str:
        return os.getenv("GITHUB_TOKEN", "")

    @property
    def github_repo(self) -> str:
        return os.getenv("GITHUB_REPO", self._yaml("github", "repo", default=""))

    @property
    def github_branch(self) -> str:
        return os.getenv("GITHUB_BRANCH", self._yaml("github", "branch", default="main"))

    @property
    def github_editable_paths(self) -> list[str]:
        return self._yaml("github", "editable_paths", default=["mirai/", "config/", "README.md"])

    @property
    def github_protected_paths(self) -> list[str]:
        return self._yaml("github", "protected_paths", default=[".env", ".env.example"])

    # ── Tor / Anonymity ───────────────────────────────────────────────────────
    @property
    def tor_enabled(self) -> bool:
        val = os.getenv("TOR_ENABLED", str(self._yaml("anonymity", "tor_enabled", default=True)))
        return val.lower() in ("1", "true", "yes")

    @property
    def tor_socks_port(self) -> int:
        return int(os.getenv("TOR_SOCKS_PORT", "9050"))

    @property
    def tor_control_port(self) -> int:
        return int(os.getenv("TOR_CONTROL_PORT", "9051"))

    @property
    def tor_password(self) -> str:
        return os.getenv("TOR_PASSWORD", "")

    @property
    def tor_rotate_every(self) -> int:
        return int(
            os.getenv(
                "TOR_ROTATE_EVERY",
                str(self._yaml("anonymity", "rotate_identity_every", default=600)),
            )
        )

    # ── Voice ─────────────────────────────────────────────────────────────────
    @property
    def voice_enabled(self) -> bool:
        val = os.getenv("VOICE_ENABLED", str(self._yaml("voice", "enabled", default=False)))
        return val.lower() in ("1", "true", "yes")

    @property
    def voice_tts_model(self) -> str:
        return os.getenv(
            "VOICE_TTS_MODEL",
            self._yaml("voice", "tts_model", default="tts_models/en/ljspeech/tacotron2-DDC"),
        )

    # ── SSH ───────────────────────────────────────────────────────────────────
    @property
    def ssh_host(self) -> str:
        return os.getenv("SSH_HOST", "")

    @property
    def ssh_user(self) -> str:
        return os.getenv("SSH_USER", "")

    @property
    def ssh_key_path(self) -> str:
        return os.getenv("SSH_KEY_PATH", "~/.ssh/id_rsa")

    @property
    def ssh_port(self) -> int:
        return int(os.getenv("SSH_PORT", "22"))

    # ── General ───────────────────────────────────────────────────────────────
    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO").upper()

    @property
    def data_dir(self) -> Path:
        raw = os.getenv("DATA_DIR", str(self._yaml("memory", "persistence_dir", default="data")))
        p = Path(raw)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def agent_name(self) -> str:
        return self._yaml("agent", "name", default="MirAI")

    @property
    def okabe_triggers(self) -> list[str]:
        return self._yaml("personality", "okabe_triggers", default=["El Psy Congroo"])

    @property
    def okabe_catchphrases(self) -> list[str]:
        return self._yaml(
            "personality",
            "catchphrases",
            default=["El Psy Kongroo."],
        )

    @property
    def context_window(self) -> int:
        return int(self._yaml("agent", "context_window", default=20))

    @property
    def allow_shell_exec(self) -> bool:
        return bool(self._yaml("agent", "allow_shell_exec", default=True))

    @property
    def kali_workspace(self) -> str:
        return self._yaml("kali", "workspace", default="/tmp/mirai_workspace")

    @property
    def kali_allowed_tools(self) -> list[str]:
        return self._yaml("kali", "allowed_tools", default=["python3", "pip3", "git"])


# Module-level singleton
settings = _Settings()
