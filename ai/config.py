"""
MirAI_OS Configuration Loader
Reads config.yaml from the user's APPDATA folder or falls back to defaults.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict


logger = logging.getLogger(__name__)

# Default configuration — edit config.yaml to override.
DEFAULTS: Dict[str, Any] = {
    # LLM settings
    "llm_provider": "openai_compatible",
    "llm_base_url": "http://localhost:1234/v1",
    "llm_api_key": "not-needed",
    "llm_model": "local-model",

    # Voice settings
    "tts_engine": "pyttsx3",
    "tts_rate": 185,
    "stt_engine": "whisper",
    "whisper_model": "base",

    # Telegram settings (leave empty to disable)
    "telegram_token": "",
    "telegram_allowed_users": [],

    # Logging
    "log_level": "INFO",
}

# Paths to look for config.yaml (in order of preference)
CONFIG_SEARCH_PATHS = [
    Path(os.getenv("APPDATA", ".")) / "MirAI_OS" / "config.yaml",
    Path(__file__).resolve().parent.parent / "config.yaml",
]


def load_config() -> Dict[str, Any]:
    """
    Load configuration from the first YAML file found in CONFIG_SEARCH_PATHS.
    Merges with DEFAULTS so missing keys always have a value.
    """
    cfg = dict(DEFAULTS)

    for path in CONFIG_SEARCH_PATHS:
        if path.exists():
            try:
                import yaml  # type: ignore

                with open(path, "r", encoding="utf-8") as fh:
                    user_cfg = yaml.safe_load(fh) or {}
                cfg.update(user_cfg)
                logger.info("Config loaded from: %s", path)
                return cfg
            except Exception as exc:
                logger.warning("Failed to load config from %s: %s", path, exc)

    logger.info("No config.yaml found – using defaults.")
    return cfg
