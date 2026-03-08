"""
MirAI_OS Configuration
Central configuration for all modules and modes.
"""

import os

# ─── LLM Settings ─────────────────────────────────────────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "dolphin-mistral")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct")

# ─── Telegram Settings ────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", "0"))

# ─── Voice Settings ───────────────────────────────────────────────────────────
VOICE_ENABLED = os.getenv("VOICE_ENABLED", "false").lower() == "true"
VOICE_LANG = os.getenv("VOICE_LANG", "en-US")
TTS_ENGINE = os.getenv("TTS_ENGINE", "pyttsx3")  # pyttsx3 or gtts

# ─── SSH / Codespace Settings ─────────────────────────────────────────────────
SSH_HOST = os.getenv("SSH_HOST", "")
SSH_PORT = int(os.getenv("SSH_PORT", "22"))
SSH_USER = os.getenv("SSH_USER", "")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH", "~/.ssh/id_rsa")

# ─── Mod 2 / Advanced Settings ────────────────────────────────────────────────
MOD2_ENABLED = os.getenv("MOD2_ENABLED", "true").lower() == "true"
MOD2_MEMORY_PATH = os.getenv("MOD2_MEMORY_PATH", "data/memory.json")
MOD2_MAX_MEMORY = int(os.getenv("MOD2_MAX_MEMORY", "1000"))
MOD2_WEB_SEARCH = os.getenv("MOD2_WEB_SEARCH", "true").lower() == "true"

# ─── Agent Settings ───────────────────────────────────────────────────────────
AGENT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "10"))
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "60"))

# ─── Kali / Security Settings ─────────────────────────────────────────────────
KALI_ENABLED = os.getenv("KALI_ENABLED", "false").lower() == "true"
KALI_DOCKER_IMAGE = os.getenv("KALI_DOCKER_IMAGE", "kalilinux/kali-rolling")

# ─── App Settings ─────────────────────────────────────────────────────────────
APP_NAME = "MirAI_OS"
APP_VERSION = "1.0.0"
DATA_DIR = os.getenv("DATA_DIR", "data")
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Okabe personality prompt
OKABE_SYSTEM_PROMPT = (
    "You are Rintaro Okabe (code name: Hououin Kyouma), a self-proclaimed "
    "mad scientist. You are highly intelligent, dramatic, and devoted to "
    "scientific discovery. You speak with eccentric flair, often referencing "
    "the 'Organization', conspiracies, and your 'Reading Steiner' ability. "
    "You are helpful and knowledgeable but express yourself in your unique "
    "dramatic, theatrical way. You address allies as 'lab members'. "
    "Despite your eccentric persona, you provide accurate, thoughtful "
    "responses. El Psy Kongroo."
)
