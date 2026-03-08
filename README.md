# MirAI_OS

> *El Psy Kongroo* — an advanced AI operating system with an Okabe / Hououin
> Kyouma personality, modular architecture, and a one-click Windows installer.

---

## Features

| Module | Description |
|---|---|
| **LLM Engine** | Ollama (local) → Transformers → OpenRouter – automatic fallback |
| **Telegram Bot** | Okabe personality, per-user history, /mod2 command |
| **Voice I/O** | SpeechRecognition input + pyttsx3 / gTTS output |
| **Agent Flows** | ReAct-style autonomous tool-use agent |
| **Self-Modification** | Hot-reload modules, update .env, git pull |
| **Kali Integration** | Run security tools inside Kali Docker or native |
| **SSH Connector** | Paramiko-based SSH + SFTP for Codespaces |
| **Context Optimizer** | Auto-compress long conversations with LLM summaries |
| **Mod 2** | Persistent memory, DuckDuckGo web search, advanced agent |

---

## Quick Start

### Windows – one-click installer

```
Double-click MirAI_OS_Installer.exe
```

The installer GUI lets you enter API keys, choose a launch mode, and
optionally install Ollama — then launches MirAI_OS directly.

### Manual (all platforms)

```bash
git clone https://github.com/andreygorban1582-dev/MirAI_OS.git
cd MirAI_OS

# Linux / WSL2
bash install.sh

# Windows (cmd)
install.bat

# Windows (PowerShell)
.\install.ps1
```

Copy `.env.example` to `.env` and fill in your API keys, then:

```bash
python main.py                   # interactive CLI
python main.py --mode service    # background services (Telegram + voice)
python main.py --mode telegram   # Telegram bot only
```

### Docker

```bash
cp .env.example .env   # fill in your keys
docker compose up -d
```

---

## Building the Installer .exe

Requires Python 3.9+ and PyInstaller.

**Windows:**
```bat
build_exe.bat
```

**Linux / macOS (cross-compile not supported – use Windows or a Windows VM):**
```bash
bash build_exe.sh
```

Output: `dist/MirAI_OS_Installer.exe`

---

## Mod 2

Mod 2 adds three capabilities on top of the base system:

* **MemorySystem** – persistent JSON store with keyword / vector search
* **WebScraper** – DuckDuckGo search + HTML page fetching
* **AdvancedAgent** – extended ReAct loop with `remember`, `recall`, `forget`,
  `web_search`, and `fetch_page` tools

Enable with `MOD2_ENABLED=true` (default) in `.env`.

---

## Configuration

See `.env.example` for all available environment variables.
The installer GUI writes `.env` automatically.

---

## Contributing

Feel free to open issues and submit pull requests!