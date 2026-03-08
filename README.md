# MirAI_OS

MirAI_OS is an advanced artificial intelligence operating system designed to integrate various functionalities such as communication, autonomous operations, and more.

## Features
- Telegram Bot with Okabe Personality
- LLM Engine with OpenRouter Integration
- Voice I/O with edge-tts / SpeechRecognition
- Autonomous Agent Flows
- Mod system (`mods.py`) – drop-in Python extensions with zero changes to `main.py`
- 50+ Lab personas (`lab_personas.py`)
- Self-Modification System
- Kali Linux Integration
- Codespace / SSH Connector
- Context Optimizer
- Windows `.exe` installer via PyInstaller

## Project structure

| File | Purpose |
|---|---|
| `main.py` | Application entry-point and core orchestrator |
| `mods.py` | Mod-loader: discover, load, and call custom extension modules |
| `lab_personas.py` | Full persona library (50+ characters) |
| `MirAI_OS.spec` | PyInstaller build specification |
| `build_installer.py` | Convenience wrapper for `pyinstaller MirAI_OS.spec` |
| `smoke_test.py` | Startup smoke-test – validates the app (or built `.exe`) launches cleanly |
| `requirements.txt` | Python dependencies |

## Quick start (Python source)

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

2. Drop `my_mod.py` into the `mods/` directory – MirAI_OS loads it automatically on startup.

## Contributing
Feel free to open issues and submit pull requests to contribute!