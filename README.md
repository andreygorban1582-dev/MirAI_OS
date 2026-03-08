# MirAI_OS

MirAI_OS is an advanced artificial intelligence operating system designed to integrate various functionalities such as communication, autonomous operations, and more.

## Features
- Telegram Bot with Okabe Personality
- LLM Engine with OpenRouter Integration
- Voice I/O with edge-tts / SpeechRecognition
- Autonomous Agent Flows
- Mod system (`mods.py`) – drop-in Python extensions with zero changes to `main.py`
- 50+ Lab personas (`lab_personas.py`)
- **User Profile Settings** – per-user persistent preferences for persona, voice, temperature, and more
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
| `user_profiles.py` | User profile settings – persist per-user preferences to `profiles.json` |
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

## User Profile Settings

Each user (Telegram or CLI) can customise their experience through persistent profile settings.  Profiles are stored in `profiles.json` in the working directory.

### Telegram commands

| Command | Description |
|---|---|
| `/profile` | Show your current profile settings |
| `/setpersona <name\|auto>` | Pin a preferred persona (or use `auto` to let the orchestrator decide) |
| `/setvoice <voice>` | Set your edge-tts voice (e.g. `en-US-AriaNeural`) |
| `/settemperature <0.0–2.0>` | Adjust LLM creativity / randomness |
| `/settokens <int>` | Set maximum response length in tokens |
| `/setname <name>` | Set your display name |
| `/togglevoice` | Toggle TTS audio output on/off |
| `/toggleverbose` | Toggle verbose (reasoning trace) mode |
| `/resetprofile` | Reset all settings to defaults |

### CLI commands

In `--mode cli` enter profile commands starting with `!`:

```
!help               list all profile commands
!profile            show current settings
!setpersona L       pin persona "L Lawliet"
!setpersona auto    clear persona pin
!setvoice en-US-AriaNeural
!settemperature 0.9
!settokens 4096
!setname Okabe
!togglevoice
!toggleverbose
!resetprofile
```

### Profile fields

| Field | Default | Description |
|---|---|---|
| `preferred_persona` | `null` (auto) | Persona to use for every message |
| `llm_temperature` | `0.7` | LLM temperature (0 = deterministic, 2 = very creative) |
| `llm_max_tokens` | `2048` | Maximum tokens per response |
| `use_voice` | `false` | Enable TTS audio output |
| `tts_voice` | `en-US-GuyNeural` | edge-tts voice identifier |
| `language` | `en` | Preferred language (BCP-47) |
| `verbose_responses` | `false` | Include reasoning trace in responses |
| `display_name` | `` | Your friendly name for greetings |

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