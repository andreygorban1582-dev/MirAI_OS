# MirAI_OS

MirAI_OS is an AI operating system that runs **100% locally** using an uncensored 8B language model
(dolphin-llama3:8b via Ollama). It ships with a 24/7 RPG simulation featuring **303 characters**,
full WSL/Linux environment control via chat, a Kali Linux installer with 200+ security tools, and
an in-chat credential manager.

El Psy Kongroo. 🧪

---

## Features

| Feature | Details |
|---------|---------|
| **Local 8B uncensored LLM** | `dolphin-llama3:8b` via Ollama – no API key required |
| **303-character game** | Persistent 24/7 RPG simulation – combat, XP, economy, leaderboard |
| **WSL/Linux control** | AI executes shell commands in your environment via chat |
| **Credential prompting** | AI asks for credentials interactively in the chat |
| **Kali Linux installer** | 200+ security tools, Ollama, Python venv, systemd service |
| **Telegram bot** | Full bot mode with the same capabilities |
| **Docker support** | `docker-compose up` for a fully containerised stack |
| **OpenRouter fallback** | Uses cloud LLM if Ollama is unavailable |

---

## Quick Start

### Option A – Kali Linux / WSL2 (recommended)

```bash
git clone https://github.com/andreygorban1582-dev/MirAI_OS.git
cd MirAI_OS
sudo bash install_kali.sh          # installs everything
./start.sh                         # launch interactive CLI
```

### Option B – Manual (any Linux / macOS)

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull dolphin-llama3:8b      # uncensored 8B model

# 2. Clone & set up Python
git clone https://github.com/andreygorban1582-dev/MirAI_OS.git
cd MirAI_OS
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env               # edit TELEGRAM_BOT_TOKEN etc.

# 4. Run
python main.py                     # CLI mode
python main.py --telegram          # Telegram bot mode
```

### Option C – Docker

```bash
cp .env.example .env               # fill in tokens
docker-compose up -d               # starts Ollama + pulls model + starts MirAI_OS
```

---

## Chat Commands

### Game
| Command | Description |
|---------|-------------|
| `/leaderboard` | Top 20 characters by wins |
| `/char <name>` | Character stats & abilities |
| `/gamestatus` | Game engine status |
| `/lastbattle` | Latest combat log |

### WSL / Shell Control
Just ask naturally:
```
install nmap
show disk usage
list running docker containers
run a port scan on 192.168.1.1
```
The AI wraps commands in `<SHELL>…</SHELL>` tags, executes them in your WSL/Linux
environment and returns the output.

### Credentials
| Command | Description |
|---------|-------------|
| `/creds` | List stored credential keys |
| `/set_cred KEY value` | Store a credential |

The AI will also ask for credentials when it needs them, e.g.:
> 🔑 Please provide `OPENROUTER_API_KEY`: Your OpenRouter API key

---

## Architecture

```
main.py                  ← Orchestrator (CLI + Telegram + WSL controller)
  ├── LLMClient          ← Ollama primary / OpenRouter fallback
  ├── MirAI_Orchestrator ← Routes messages, executes shell, manages creds
  └── GameEngine         ← 24/7 background simulation task
        └── characters.py  ← All 303 characters with stats & abilities
game_engine.py           ← Combat, XP, economy, state persistence
characters.py            ← 303 character definitions
install_kali.sh          ← Full Kali Linux + Ollama + tools installer
docker-compose.yml       ← Ollama + MirAI_OS containers
```

---

## The 303 Characters

Characters span 60+ universes including Steins;Gate, Attack on Titan, Naruto,
My Hero Academia, Dragon Ball, One Piece, Cyberpunk 2077, Halo, Mass Effect,
The Witcher, Elden Ring, Dark Souls, Ghost in the Shell, JoJo's Bizarre Adventure,
Bleach, Evangelion, Overwatch, League of Legends, Persona, Resident Evil,
Hollow Knight, Undertale, Portal, BioShock, Metal Gear, Fate, Re:Zero,
Jujutsu Kaisen, Solo Leveling, Marvel, DC, Star Wars, Avatar, and more.

Each character has:
- Stats: HP, Attack, Defense, Speed, Intelligence
- Level / XP / Gold
- 2–4 unique abilities
- Win/Loss record
- Alive/Knocked-out status

---

## Kali Linux Installer (`install_kali.sh`)

Installs on Kali Linux, Debian/Ubuntu, Fedora/RHEL, Arch, and WSL2:

- System packages (Python 3.11, pip, audio libs, git, curl)
- **Ollama** + `dolphin-llama3:8b` (uncensored 8B model)
- **Kali Linux toolset**: `kali-linux-default`, web tools, wireless, exploitation,
  forensics, passwords, reporting, reverse engineering, social engineering
- Individual tools on non-Kali: nmap, metasploit, hydra, aircrack-ng,
  sqlmap, wireshark, nikto, gobuster, hashcat, and 40+ more
- Python virtual environment with all dependencies
- Systemd service (Linux) or `start.sh` script (WSL2)
- `.env` configuration file

---

## Security

- All credentials are stored in `.credentials.json` (chmod 600, git-ignored)
- Shell command execution blocks destructive patterns (`rm -rf /`, fork bombs, etc.)
- Command output is truncated at 4000 characters
- Credentials are never logged or sent to external services

---

## Contributing

Issues and pull requests are welcome! El Psy Kongroo.