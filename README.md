# MirAI_OS

MirAI_OS is an advanced artificial intelligence operating system designed to integrate various functionalities such as communication, autonomous operations, and more.

Everything lives in a single file — `mirai_installer.py` — which serves as both the installer and the runtime application.

## Features

- **All-in-One Python Installer** — single `mirai_installer.py` sets up and runs the full stack
- **Custom GUI** — tkinter-based dashboard with tabs for Installer, Config, Chat, RPG Game, Kali Tools, SSH, Voice and About
- **Telegram Bot** with Okabe Rintaro personality, voice message support, and game commands
- **LLM Engine** — Ollama (llama3:8b local) with OpenRouter API fallback
- **Voice I/O** — Sesame CSM voice synthesis + Edge-TTS fallback + Speech-to-Text via SpeechRecognition
- **Multi-Persona Orchestrator** — 25+ anime/manga personas routed in parallel
- **RPG Game Engine** — characters, government elections, economy/market, crafting, exploration, quests, diplomacy
- **WSL2 Kali Linux** — 128 GB swap configuration, 200+ Kali tools integration
- **Docker** — nginx reverse-proxy container for OpenRouter API
- **Codespace SSH Connector** — paramiko-based SSH orchestration for GitHub Codespaces
- **Context Optimizer** — rolling conversation window for efficient LLM usage

## Quick Start

```bash
# Clone
git clone https://github.com/andreygorban1582-dev/MirAI_OS.git
cd MirAI_OS

# Install Python deps
pip install -r requirements.txt

# Launch the GUI installer & app
python mirai_installer.py

# Or run headless install
python mirai_installer.py --install

# CLI chat mode
python mirai_installer.py --mode cli

# Telegram bot mode
TELEGRAM_BOT_TOKEN=your_token python mirai_installer.py --mode telegram
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API key | — |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | — |
| `TELEGRAM_CHAT_ID` | Allowed chat ID (optional) | — |
| `OLLAMA_HOST` | Ollama server URL | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Local LLM model name | `llama3:8b` |
| `USE_LOCAL_LLM` | Enable Ollama backend | `true` |
| `SESAME_CSM_ENABLED` | Enable Sesame CSM voice | `true` |
| `SESAME_CSM_URL` | Sesame CSM API endpoint | `http://127.0.0.1:8860/v1/audio/speech` |
| `SSH_HOST` | Codespace SSH host | — |
| `SSH_USER` | SSH username | `root` |
| `SSH_KEY_PATH` | Path to SSH private key | `~/.ssh/id_rsa` |

## Architecture

```
mirai_installer.py
├── Section 1  – Configuration (Config dataclass, env loading)
├── Section 2  – Installer (WSL2 swap, Docker, Ollama, Kali tools, pip)
├── Section 3  – LLM Client (Ollama → OpenRouter → fallback)
├── Section 4  – Voice I/O (Sesame CSM, Edge-TTS, STT)
├── Section 5  – Codespaces SSH Orchestration
├── Section 6  – Kali Tool Manager
├── Section 7  – Personas (25+ anime characters)
├── Section 8  – Orchestrator (multi-agent routing + synthesis)
├── Section 9  – RPG Game Engine (characters, economy, quests, …)
├── Section 10 – Telegram Bot (commands, voice messages)
├── Section 11 – Custom GUI (tkinter, 8 tabs)
├── Section 12 – CLI Mode
└── Section 13 – Main Entry Point
```

## Contributing

Feel free to open issues and submit pull requests to contribute!