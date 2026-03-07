"""
MirAI OS — Configuration loader
Loads settings.yaml + .env and exposes a unified config object.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "settings.yaml"
NODES_PATH = ROOT / "config" / "nodes.yaml"
ENV_PATH = ROOT / ".env"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


class Config:
    """Unified configuration object."""

    def __init__(self) -> None:
        # Load .env first so env vars override yaml
        load_dotenv(ENV_PATH if ENV_PATH.exists() else ROOT / "config" / ".env.example")
        self._data = _load_yaml(CONFIG_PATH)
        self.nodes = _load_yaml(NODES_PATH).get("nodes", [])

    # ── generic nested access ───────────────────────────────
    def get(self, *keys: str, default: Any = None) -> Any:
        node = self._data
        for k in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(k, default)
        return node

    # ── convenience properties ──────────────────────────────
    @property
    def openrouter_keys(self) -> list[str]:
        keys = []
        for i in range(1, 5):
            k = os.getenv(f"OPENROUTER_KEY_{i}", "")
            if k and not k.startswith("sk-or-v1-REPLACE"):
                keys.append(k)
        return keys

    @property
    def telegram_token(self) -> str:
        return os.getenv("TELEGRAM_BOT_TOKEN", "")

    @property
    def telegram_admin_ids(self) -> list[int]:
        raw = os.getenv("TELEGRAM_ADMIN_IDS", "")
        return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]

    @property
    def github_token(self) -> str:
        return os.getenv("GITHUB_TOKEN", "")

    @property
    def github_repo(self) -> str:
        return os.getenv("GITHUB_REPO", "")

    @property
    def redis_url(self) -> str:
        return os.getenv("REDIS_URL", "redis://localhost:6379/0")

    @property
    def secret_key(self) -> str:
        return os.getenv("MIRAI_SECRET_KEY", "changeme")

    @property
    def llm(self) -> dict:
        return self._data.get("llm", {})

    @property
    def memory(self) -> dict:
        return self._data.get("memory", {})

    @property
    def personality(self) -> dict:
        return self._data.get("personality", {})

    @property
    def voice(self) -> dict:
        return self._data.get("voice", {})

    @property
    def kali_tools(self) -> dict:
        return self._data.get("kali_tools", {})

    @property
    def agents(self) -> dict:
        return self._data.get("agents", {})

    @property
    def network(self) -> dict:
        return self._data.get("network", {})

    @property
    def self_modification(self) -> dict:
        return self._data.get("self_modification", {})

    def active_nodes(self) -> list[dict]:
        return [n for n in self.nodes if n.get("status") == "active"]

    def get_node(self, node_id: str) -> Optional[dict]:
        for n in self.nodes:
            if n["id"] == node_id:
                return n
        return None


# Global singleton
cfg = Config()
