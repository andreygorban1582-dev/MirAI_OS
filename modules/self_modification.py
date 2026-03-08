"""
Self-Modification System – allows MirAI_OS to update its own config
and behaviour at runtime, and optionally pull the latest code from GitHub.
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SelfModification:
    """Runtime self-modification capabilities for MirAI_OS."""

    def __init__(self) -> None:
        self.root = Path(__file__).resolve().parent.parent

    # ── config updates ────────────────────────────────────────────────────────

    def update_env(self, key: str, value: str) -> None:
        """Set an environment variable and persist it to .env file."""
        os.environ[key] = value
        env_path = self.root / ".env"
        lines: list[str] = []
        found = False
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith(f"{key}="):
                    lines.append(f"{key}={value}")
                    found = True
                else:
                    lines.append(line)
        if not found:
            if lines:
                lines.append(f"{key}={value}")
            else:
                lines.append(f"{key}={value}")
        env_path.write_text("\n".join(lines) + "\n")
        logger.info("Updated env var %s", key)

    def reload_config(self) -> None:
        """Hot-reload the config module."""
        import config  # noqa: PLC0415

        importlib.reload(config)
        logger.info("Config reloaded.")

    # ── code updates ──────────────────────────────────────────────────────────

    def pull_latest(self) -> str:
        """Pull the latest code from git origin."""
        import subprocess  # noqa: S404

        try:
            result = subprocess.run(  # noqa: S603,S607
                ["git", "pull", "--ff-only"],
                capture_output=True,
                text=True,
                cwd=str(self.root),
                timeout=30,
            )
            output = result.stdout.strip() or result.stderr.strip()
            logger.info("git pull: %s", output)
            return output
        except Exception as exc:
            logger.error("git pull failed: %s", exc)
            return str(exc)

    def reload_module(self, module_name: str) -> str:
        """Hot-reload a named module from the modules package."""
        full_name = f"modules.{module_name}"
        if full_name not in sys.modules:
            return f"Module '{module_name}' not loaded."
        try:
            importlib.reload(sys.modules[full_name])
            return f"Module '{module_name}' reloaded."
        except Exception as exc:
            return f"Reload error: {exc}"

    # ── introspection ─────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return current runtime status information."""
        return {
            "python": sys.version,
            "cwd": str(Path.cwd()),
            "root": str(self.root),
            "loaded_modules": [m for m in sys.modules if m.startswith("modules")],
            "env_keys": [k for k in os.environ if k.startswith("MIRAI")
                         or k.startswith("OLLAMA")
                         or k.startswith("TELEGRAM")
                         or k.startswith("OPENROUTER")],
        }
