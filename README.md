# MirAI_OS

MirAI_OS is an advanced artificial intelligence operating system designed to integrate various functionalities such as communication, autonomous operations, and more.

## Features
- **Dolphin-Mistral** local LLM via Ollama — runs entirely on Codespaces
- Telegram Bot with Okabe Personality
- LLM Engine with OpenRouter Integration (optional cloud fallback)
- Voice I/O with edge-tts / SpeechRecognition
- Autonomous Agent Flows
- Unified AI Agent Orchestrator (`orchestrator.py`) — 400+ repo integrations
- Mod system (`mods.py`) — drop-in Python extensions with zero changes to `main.py`
- 50+ Lab personas (`lab_personas.py`)
- Self-Modification System
- Kali Linux Integration
- Codespace / SSH Connector
- Context Optimizer
- Windows `.exe` installer via PyInstaller

## Project structure

| File / Directory | Purpose |
|---|---|
| `main.py` | Application entry-point and core orchestrator |
| `mods.py` | Mod-loader: discover, load, and call custom extension modules |
| `lab_personas.py` | Full persona library (50+ characters) |
| `orchestrator.py` | Unified AI Agent Orchestrator (Mod 2) — skills, agents, FastAPI |
| `install.sh` | **One-command installer** — Python deps + Ollama + Dolphin-Mistral |
| `.devcontainer/` | GitHub Codespaces devcontainer configuration |
| `scripts/kali_setup.sh` | Kali Linux customization script |
| `MirAI_OS.spec` | PyInstaller build specification |
| `build_installer.py` | Convenience wrapper for `pyinstaller MirAI_OS.spec` |
| `smoke_test.py` | Startup smoke-test — validates the app launches cleanly |
| `requirements.txt` | Python dependencies |

## Quick start — GitHub Codespaces (recommended)

1. Click **Code → Codespaces → Create codespace on main** (or this branch).
2. The devcontainer runs `install.sh` automatically — it installs Python deps,
   Ollama, and pulls the **Dolphin-Mistral (4B)** model.
3. Once the terminal is ready:

```bash
python main.py --mode cli
```

That's it — the LLM runs locally inside the Codespace, no API keys required.

## Quick start — local Linux / macOS

```bash
# 1. Clone
git clone https://github.com/andreygorban1582-dev/MirAI_OS.git
cd MirAI_OS

# 2. Run the installer (installs deps, Ollama, and Dolphin-Mistral)
bash install.sh

# 3. Run (CLI mode)
python main.py --mode cli

# 4. Run (Telegram bot mode — requires TELEGRAM_BOT_TOKEN in .env)
python main.py --mode telegram
```

## Quick start — manual (Python source)

```bash
# 1. Clone
git clone https://github.com/andreygorban1582-dev/MirAI_OS.git
cd MirAI_OS

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure (copy and edit the example env file)
# Set OPENROUTER_API_KEY and optionally TELEGRAM_BOT_TOKEN in .env

# 5. Run (CLI mode)
python main.py --mode cli

# 6. Run (Telegram bot mode)
python main.py --mode telegram
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `USE_OLLAMA` | `true` (Codespace) | Use Ollama for local LLM inference |
| `OLLAMA_MODEL` | `dolphin-mistral` | Model name for Ollama |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server address |
| `OPENROUTER_API_KEY` | *(empty)* | Cloud LLM fallback via OpenRouter |
| `TELEGRAM_BOT_TOKEN` | *(empty)* | Telegram bot token |
| `KALI_TOOLS_ENABLED` | `true` | Enable Kali Linux tool integration |

## Building a Windows `.exe`

Run the helper script (or invoke PyInstaller directly):

```bash
# Install PyInstaller (included in requirements.txt)
pip install pyinstaller

# Build using the helper
python build_installer.py

# Or directly
pyinstaller MirAI_OS.spec
```

The resulting executable is written to `dist/MirAI_OS.exe` (Windows) or `dist/MirAI_OS` (Linux/macOS).

## Smoke test

After building (or to test the Python source), run:

```bash
# Test the Python source entry-point
python smoke_test.py

# Test the built executable (Windows)
python smoke_test.py --exe dist/MirAI_OS.exe
```

A zero exit code means the application started and reported its help/usage correctly.

## Writing a mod

1. Create a Python file, e.g. `my_mod.py`:

```python
MOD_NAME    = "my_mod"
MOD_VERSION = "1.0.0"

def setup(bot, llm, ctx):
    print(f"[{MOD_NAME}] loaded!")

def on_message(message: str, ctx: dict) -> str | None:
    if message.lower() == "ping":
        return "pong"
    return None  # pass through to normal LLM pipeline
```

2. Drop `my_mod.py` into the `mods/` directory — MirAI_OS loads it automatically on startup.

## Contributing
Feel free to open issues and submit pull requests to contribute!