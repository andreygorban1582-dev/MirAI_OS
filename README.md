# MirAI_OS

> **"El Psy Congroo."**  
> *Autonomous AI agent for Kali Linux / WSL2 on the Lenovo Legion Go.*

MirAI_OS is a fully autonomous AI assistant that runs on **Kali Linux inside WSL2** on your Legion Go. It combines a powerful LLM (via OpenRouter), a Telegram bot interface, self-modification capabilities (like GitHub Copilot on itself), voice I/O, Tor-based anonymity, and direct shell access to your Kali tools — all installed with a single command.

---

## Table of Contents

1. [Features](#features)  
2. [Architecture & Code Explanation](#architecture--code-explanation)  
3. [Quick Install (One Command)](#quick-install-one-command)  
4. [Windows / Legion Go Installer](#windows--legion-go-installer)  
5. [Configuration](#configuration)  
6. [Running MirAI](#running-mirai)  
7. [Telegram Commands](#telegram-commands)  
8. [Self-Modification System](#self-modification-system)  
9. [Anonymity & Tor](#anonymity--tor)  
10. [Voice I/O](#voice-io)  
11. [Building a Windows .exe](#building-a-windows-exe)  
12. [Security Notes](#security-notes)  

---

## Features

| Feature | Module | Status |
|---|---|---|
| Conversational AI (OpenRouter / GPT-4o) | `mirai/llm.py` | ✅ |
| Telegram Bot with Okabe personality | `mirai/telegram_bot.py` | ✅ |
| Conversation memory & context optimizer | `mirai/memory.py` | ✅ |
| Self-modification via GitHub API | `mirai/self_mod.py` | ✅ |
| Copilot-like repo read/write | `mirai/github_client.py` | ✅ |
| Kali Linux tool execution | `mirai/kali_tools.py` | ✅ |
| Tor anonymity & identity rotation | `mirai/anonymity.py` | ✅ |
| Voice I/O (TTS + STT) | `mirai/voice.py` | ✅ |
| SSH / Codespace connector | `mirai/ssh_connector.py` | ✅ |
| WSL2 / Kali one-shot installer | `scripts/install_wsl.sh` | ✅ |
| Windows batch installer | `installer/install_windows.bat` | ✅ |
| Windows .exe builder (PyInstaller) | `installer/build_installer.py` | ✅ |

---

## Architecture & Code Explanation

```
MirAI_OS/
├── main.py                    ← Entry point (CLI + Telegram launcher)
├── mirai/
│   ├── __init__.py            ← Package init, exports Agent
│   ├── settings.py            ← Settings loader (YAML + .env)
│   ├── agent.py               ← Core orchestrator (THE BRAIN)
│   ├── llm.py                 ← LLM engine (OpenRouter / GPT-4o)
│   ├── memory.py              ← Conversation memory & context pruning
│   ├── telegram_bot.py        ← Telegram bot with Okabe personality
│   ├── github_client.py       ← GitHub read/write (Copilot-like)
│   ├── self_mod.py            ← Self-modification system
│   ├── kali_tools.py          ← Safe Kali Linux shell executor
│   ├── anonymity.py           ← Tor integration & identity rotation
│   ├── voice.py               ← TTS (Coqui) + STT (SpeechRecognition)
│   └── ssh_connector.py       ← SSH / Codespace tunnel
├── config/
│   └── config.yaml            ← Non-secret configuration
├── scripts/
│   └── install_wsl.sh         ← Kali / WSL2 one-shot installer
├── installer/
│   ├── install_windows.bat    ← Windows installer (runs on Legion Go)
│   └── build_installer.py     ← Builds MirAI.exe via PyInstaller
├── requirements.txt
├── setup.py
└── .env.example               ← Copy to .env and fill in secrets
```

### How each module works

#### `mirai/settings.py` — Settings Loader
Reads `config/config.yaml` for structured defaults and `.env` for secrets.  
**Why two layers?** Structured config in YAML is version-controlled and readable. Secrets (API keys) stay in `.env` which is git-ignored. Environment variables always override both, making CI/CD painless.

#### `mirai/llm.py` — LLM Engine
Wraps the **OpenAI-compatible SDK** pointed at **OpenRouter's API** so you can use any model (GPT-4o, Claude, Mistral, etc.) with one config change.  
Key methods:
- `chat(messages)` — sends a full conversation, returns the reply as a string  
- `stream(messages)` — same but yields text chunks as they arrive  
- `count_tokens(messages)` — token counting via `tiktoken` for context management

#### `mirai/memory.py` — Conversation Memory
Stores all user/assistant turns in a **rolling window** (default 50 messages).  
When the window fills, oldest non-system messages are pruned so the context never exceeds the model's token limit.  
Memory is persisted to `data/memory.json` so conversations survive restarts.

#### `mirai/agent.py` — Core Agent ★
This is where everything comes together. `Agent.chat(user_message)`:
1. Adds the user message to memory
2. Sends the full conversation to the LLM
3. **Parses tool-call directives** embedded in the reply:
   - `!!SHELL!! <cmd>` → runs a shell command via `KaliTools`
   - `!!SELFMOD!! <path> :: <instruction>` → modifies a source file
   - `!!GITHUB_READ!! <path>` → reads a file from the repo
   - `!!GITHUB_WRITE!! <path> :: <content>` → writes to the repo
4. Replaces directives with their output
5. Returns the cleaned reply

This tool-call protocol allows the LLM to **autonomously use system tools** without a complex function-calling API — it simply embeds directives in its text output.

#### `mirai/telegram_bot.py` — Telegram Interface
Runs an async bot using `python-telegram-bot` v21.  
Every incoming message is forwarded to `Agent.chat()`.  
**Okabe personality**: if your message contains "El Psy Congroo" or other trigger phrases, MirAI responds with a Steins;Gate catchphrase before the actual reply.  
Access control via `TELEGRAM_ALLOWED_USERS` — only listed Telegram user IDs can interact.

#### `mirai/github_client.py` — Copilot-like Repo Access
Uses **PyGithub** to read and write files in the repository via the GitHub API.  
MirAI can inspect its own source code, propose improvements, and commit them directly.  
**Safety**: a whitelist (`editable_paths`) and blacklist (`protected_paths`) in `config.yaml` ensure the agent can't accidentally overwrite `.env` or installer scripts.

#### `mirai/self_mod.py` — Self-Modification
Orchestrates the read → reason → write loop:
1. Reads the current file from GitHub
2. Sends it to the LLM with an instruction ("fix this bug", "add this feature")
3. The LLM returns the complete new file content
4. Writes it back to GitHub as a timestamped commit

`review_self()` asks the LLM to audit all source files and report bugs/issues.

#### `mirai/anonymity.py` — Tor Integration
Routes all HTTP requests through the local Tor SOCKS5 proxy.  
Uses `stem` to send `NEWNYM` signals to Tor's control port, rotating the exit-node IP.  
`IdentityRotator` is a background thread that rotates automatically every N seconds (configurable in `config.yaml`).

#### `mirai/kali_tools.py` — Shell Executor
Safely runs approved CLI tools on the Kali host.  
- **Whitelist**: only tools in `config.kali.allowed_tools` may be invoked  
- **No shell=True**: commands are split with `shlex` to prevent injection  
- **Timeout**: each command has a 60-second timeout  
- **Workspace**: all commands run in `/tmp/mirai_workspace`, never in `/` or `~`

#### `mirai/voice.py` — Voice I/O
- **TTS**: uses **Coqui TTS** to synthesise speech from text (runs offline)  
- **STT**: uses **SpeechRecognition** (Google by default; Vosk for offline)  
- Disabled by default (`VOICE_ENABLED=false`) — set `true` in `.env` to activate  
- WSL2 note: the installer configures PulseAudio TCP forwarding so audio works

#### `mirai/ssh_connector.py` — SSH / Codespace
Opens an SSH tunnel to any remote host (e.g. a GitHub Codespace).  
Useful when you want MirAI running in the cloud while you chat via Telegram from your Legion Go.

---

## Quick Install (One Command)

**Inside Kali Linux (WSL2 or native):**

```bash
curl -fsSL https://raw.githubusercontent.com/andreygorban1582-dev/MirAI_OS/main/scripts/install_wsl.sh | bash
```

The script will:
- Install system packages (Tor, PortAudio, build tools)
- Clone the repository to `~/MirAI_OS`
- Create a Python virtual environment
- Install all Python packages
- Create a `.env` file and prompt for API keys
- Configure Tor + proxychains
- Create the `mirai` launcher command

---

## Windows / Legion Go Installer

1. **Download** `installer/install_windows.bat` from this repo  
2. **Right-click** → **Run as Administrator**  
3. The script will:
   - Enable WSL2 + Virtual Machine Platform
   - Install Kali Linux from the Microsoft Store
   - Run the Kali installer inside WSL2 automatically
   - Create a Desktop shortcut

> ⚠️ A reboot may be required after enabling WSL2 features. Re-run the installer after rebooting.

---

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
nano .env   # or use any text editor
```

Required values:

| Variable | Where to get it |
|---|---|
| `OPENROUTER_API_KEY` | https://openrouter.ai/keys |
| `TELEGRAM_BOT_TOKEN` | Talk to [@BotFather](https://t.me/BotFather) on Telegram |
| `GITHUB_TOKEN` | https://github.com/settings/tokens (needs `repo` scope) |

Optional:

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_MODEL` | `openai/gpt-4o` | Any OpenRouter model slug |
| `TELEGRAM_ALLOWED_USERS` | *(blank = public)* | Comma-separated Telegram user IDs |
| `TOR_ENABLED` | `true` | Route traffic through Tor |
| `VOICE_ENABLED` | `false` | Enable microphone + speaker |
| `LOG_LEVEL` | `INFO` | DEBUG / INFO / WARNING / ERROR |

---

## Running MirAI

```bash
# Interactive terminal session
mirai
# or
python main.py cli

# Telegram bot (blocking – runs until Ctrl+C)
mirai telegram
# or
python main.py telegram

# Self-modify a file
mirai selfmod "add rate limiting to the LLM engine"

# Code review
mirai review

# Rotate Tor identity and show new IP
mirai anon
```

---

## Telegram Commands

Once the bot is running, open Telegram and message your bot:

| Command | Description |
|---|---|
| `/start` | Show welcome message and available commands |
| `/status` | Current exit IP, Tor status, memory size |
| `/run <cmd>` | Execute a shell command (e.g. `/run nmap -sV localhost`) |
| `/memory` | Show the last 10 conversation messages |
| `/selfmod <instruction>` | Modify MirAI's own code |
| `/anon` | Rotate Tor identity |
| `/voice` | Toggle voice mode |
| *(any text)* | Chat with MirAI |

---

## Self-Modification System

MirAI can modify its own source code through the Telegram bot or CLI:

```
/selfmod add retry logic to the LLM engine when API calls fail
```

Or via CLI:
```bash
mirai selfmod "add retry logic to the LLM engine when API calls fail"
```

What happens:
1. MirAI reads `mirai/llm.py` from GitHub
2. Sends it to GPT-4o with the instruction
3. GPT-4o returns a new version of the file
4. MirAI commits it to the repo with a timestamped message

Use `--dry-run` to preview changes without committing:
```bash
mirai selfmod --dry-run "refactor the memory module"
```

**Protected files** (cannot be self-modified):
- `.env`, `.env.example`
- `installer/`
- `scripts/`

---

## Anonymity & Tor

MirAI routes all outbound HTTP through Tor by default.

```bash
# See current exit IP
mirai anon

# In Telegram
/anon
```

To disable Tor (not recommended):
```
TOR_ENABLED=false
```

Tor must be running on the system:
```bash
sudo service tor start
```

Identity auto-rotation interval is configurable in `config.yaml`:
```yaml
anonymity:
  rotate_identity_every: 600  # seconds
```

---

## Voice I/O

Enable in `.env`:
```
VOICE_ENABLED=true
```

Then restart MirAI. It will:
- **Speak** every reply using Coqui TTS (offline)
- **Listen** for your voice input via the microphone

WSL2 users: the installer configures PulseAudio TCP forwarding automatically.
You may need to install a PulseAudio server on Windows (e.g. PulseAudio for Windows or VcXsrv).

---

## Building a Windows .exe

On Windows, inside the virtual environment:

```bash
python installer/build_installer.py
```

Output: `dist/MirAI.exe` — a standalone executable that runs MirAI without requiring Python to be installed.

---

## Security Notes

- **Never commit `.env`** — it is in `.gitignore` by default.
- The GitHub token in `.env` grants write access to your repo. Treat it like a password.
- `allow_shell_exec: true` in `config.yaml` allows MirAI to run shell commands. The whitelist in `kali.allowed_tools` limits which executables can be used.
- Tor provides **network anonymity** but not endpoint anonymity. Do not log into personal accounts while relying solely on Tor for privacy.
- Self-modification is powerful. Always review commits made by MirAI in your repo's commit history.

## Contributing
Feel free to open issues and submit pull requests to contribute!