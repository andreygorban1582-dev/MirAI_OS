# MirAI_OS

> **Advanced AI assistant optimised for the Lenovo Legion Go (Windows 11, AMD Ryzen Z1 Extreme)**

## Features

| Module | Description |
|---|---|
| **Core Orchestrator** | Routes requests between all modules; event/hook system |
| **Personality Engine** | Okabe-style conversational persona with history |
| **LLM Integration** | OpenAI-compatible client (LM Studio, Ollama, OpenAI) |
| **Voice System** | pyttsx3 TTS + Whisper STT for hands-free use |
| **Telegram Bot** | Remote AI access from your phone |
| **Self-Modification** | Hot-reload modules, patch config, install plugins at runtime |

---

## Building the Installer (Windows / Legion Go)

### Prerequisites

| Tool | Download |
|---|---|
| Python 3.10+ | <https://www.python.org/downloads/> |
| Inno Setup 6 | <https://jrsoftware.org/isinfo.php> |
| (Optional) UPX | <https://upx.github.io/> |

### One-command build

Open **PowerShell** in the repository root and run:

```powershell
.\build.ps1
```

This will:

1. Create a `.venv` virtual environment and install all dependencies
2. Bundle the app with **PyInstaller** (UAC elevation enabled)
3. Compile `installer/setup.iss` with **Inno Setup**
4. Output `dist\MirAI_OS_Setup.exe` — a single installer ready to use

> The installer requests **administrator privileges** automatically on launch
> (required for system-level integration on the Legion Go).

---

## Repository Structure

```
MirAI_OS/
├── ai/
│   ├── main.py          ← Entry point (start here)
│   └── config.py        ← Config loader (reads config.yaml / APPDATA)
├── mods/
│   ├── core_orchestrator.py
│   ├── personality_engine.py
│   ├── llm_integration.py
│   ├── voice_system.py
│   ├── telegram_bot.py
│   └── self_modification.py
├── installer/
│   └── setup.iss        ← Inno Setup script (produces MirAI_OS_Setup.exe)
├── assets/
│   └── icon.ico         ← (optional) custom tray icon
├── config.yaml          ← Default configuration (copied to %APPDATA%\MirAI_OS\)
├── requirements.txt     ← Python dependencies
├── MirAI_OS.spec        ← PyInstaller spec (UAC admin, bundled mods)
└── build.ps1            ← One-click Windows build script
```

---

## Configuration

After installation the config file lives at:

```
%APPDATA%\MirAI_OS\config.yaml
```

Edit it to point at your local LLM server, add your Telegram bot token, etc.
See `config.yaml` in the repo root for full documentation of every option.

---

## Running Without the Installer

```powershell
# Install dependencies
pip install -r requirements.txt

# Start MirAI
python ai/main.py
```

---

## Usage

Type messages at the `You:` prompt.
Say `quit` or `exit` to shut down.
Voice input starts automatically if a microphone is detected.

## Contributing
Feel free to open issues and submit pull requests to contribute!