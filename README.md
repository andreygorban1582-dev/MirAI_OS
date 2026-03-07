# MirAI OS

```
 ███╗   ███╗██╗██████╗  █████╗ ██╗      ██████╗ ███████╗
 ████╗ ████║██║██╔══██╗██╔══██╗██║     ██╔═══██╗██╔════╝
 ██╔████╔██║██║██████╔╝███████║██║     ██║   ██║███████╗
 ██║╚██╔╝██║██║██╔══██╗██╔══██║██║     ██║   ██║╚════██║
 ██║ ╚═╝ ██║██║██║  ██║██║  ██║███████╗╚██████╔╝███████║
 ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝
                                                    OS v0.1.0
  Future Gadget Lab #8  |  Legion Go Node  |  El Psy Kongroo.
```

**MirAI OS** is a fully autonomous AI operative running on your Legion Go as a 24/7 server. Controlled entirely via Telegram with a Watchdogs terminal aesthetic. Personality: Hououin Kyouma (Okabe Rintaro) from Steins;Gate.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     TELEGRAM BOT                         │
│            (Watchdogs Terminal UI + Voice)               │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                   ORCHESTRATOR                           │
│          (ReAct Loop — Reason → Act → Observe)          │
└──┬──────┬────────┬──────────┬─────────────┬─────────────┘
   │      │        │          │             │
   ▼      ▼        ▼          ▼             ▼
  LLM   Memory  Agents    Kali Tools   Self-Modify
  Layer  Engine  (Web,     (nmap,       (GitHub,
  (4-key  (Redis  Code,     sqlmap,      code inject,
  OpenR.) +Chroma SSH,      hydra...)    key mgmt)
          +SQLite) Bash)
                        │
              ┌─────────▼──────────┐
              │  COMPUTE NETWORK   │
              │  Legion Go (local) │
              │  Codespace 1-4     │
              │  (SSH workers)     │
              └────────────────────┘
```

---

## Features

| Feature | Implementation |
|---|---|
| Main LLM | Qwen 3.5 9B (JOSIEFIED) via OpenRouter |
| API Key Rotation | 4 OpenRouter keys, round-robin + fallback |
| Unlimited Context | Redis (short) + SQLite summaries (medium) + ChromaDB vectors (long) |
| Personality | Okabe Rintaro / Hououin Kyouma — Steins;Gate |
| Interface | Telegram bot — Watchdogs terminal aesthetic |
| Voice In | Whisper STT (local, offline) |
| Voice Out | Sesame CSM (character.ai open-source) |
| Web Browsing | Playwright Chromium (headless) |
| Code Execution | Python + Bash in Kali WSL2 |
| Pentesting | Full Kali Linux tool access |
| Remote Nodes | SSH to 4 GitHub Codespaces |
| Self-Modification | Injects code, adds API/SSH keys, commits to GitHub |
| Platform | Legion Go (Z1 Extreme, 16GB RAM + 128GB swap) |
| Cost | **100% Free** (OpenRouter free tiers, GitHub free, Telegram free) |

---

## Hardware

| Component | Spec |
|---|---|
| Device | Lenovo Legion Go |
| CPU | AMD Z1 Extreme (8c/16t) |
| RAM | 16GB (+ 128GB swap) |
| OS (host) | Windows 11 |
| OS (AI) | Kali Linux on WSL2 |
| Role | 24/7 AI server |

---

## Quick Start

### 1. Prerequisites

**On Windows:**
```powershell
# Run as Administrator in PowerShell
wsl --install -d kali-linux
wsl --set-default kali-linux
```

**Configure WSL2 limits** (run in PowerShell):
```powershell
.\scripts\configure_wslconfig.ps1
wsl --shutdown
```

### 2. Install in WSL2 Kali

```bash
# Inside Kali WSL2
git clone https://github.com/YOUR_USERNAME/MirAI_OS.git
cd MirAI_OS
bash scripts/setup_wsl.sh
```

### 3. Configure 128GB Swap

```bash
sudo bash scripts/setup_swap.sh 128
```

### 4. Set API Keys

```bash
nano .env
```

Fill in:
```env
OPENROUTER_KEY_1=sk-or-v1-...
OPENROUTER_KEY_2=sk-or-v1-...
OPENROUTER_KEY_3=sk-or-v1-...
OPENROUTER_KEY_4=sk-or-v1-...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ADMIN_IDS=YOUR_TELEGRAM_USER_ID
GITHUB_TOKEN=ghp_...
GITHUB_REPO=YOUR_USERNAME/MirAI_OS
```

### 5. (Optional) Setup Voice

```bash
bash scripts/setup_sesame_csm.sh
```

### 6. Run

```bash
source venv/bin/activate
python main.py
```

**For 24/7 operation:**
```bash
screen -S mirai python main.py
# Detach: Ctrl+A, D
# Reattach: screen -r mirai
```

---

## Telegram Commands

| Command | Description |
|---|---|
| `/start` | Boot screen + welcome |
| `/help` | Full command manual |
| `/status` | System status panel |
| `/keys` | OpenRouter key pool health |
| `/nodes` | Compute node grid |
| `/kali <cmd>` | Run any Kali command |
| `/scan <host>` | Quick nmap scan |
| `/web <url>` | Browse a URL |
| `/code <python>` | Execute Python |
| `/bash <cmd>` | Execute Bash |
| `/push` | Commit + push to GitHub |
| `/memory` | Memory system stats |
| Voice message | Speak to MirAI → Voice reply |
| Any text | Natural language — fully autonomous |

---

## Self-Modification

MirAI can modify itself. Just tell it:

```
"Add this Python code as a new capability: [paste code]"
"Save this API key: NAME=value"
"Add this SSH key and connect to node X: [paste key]"
"Commit everything and push to GitHub"
```

MirAI will inject the code into `data/capabilities/`, save keys to `.env`, and push to GitHub automatically.

---

## Adding GitHub Codespace Nodes

1. Create a Codespace on GitHub (free 60 hrs/month per account)
2. Get the SSH connection details from Codespace settings
3. Tell MirAI in Telegram:
   ```
   "Add this SSH key for codespace-1: [paste private key]"
   "Register codespace-1 at HOST:22 user codespace"
   ```
4. MirAI auto-tests the connection and adds it to the node grid

---

## Architecture Details

### Memory System (Unlimited Context)

```
Short-term  → Redis         → Last 50 messages (fast lookup)
Medium-term → SQLite        → LLM-compressed summaries (every 20 msgs)
Long-term   → ChromaDB      → Semantic vector search (truly unlimited)

Context building:
  [System Prompt]
  + [Top 8 relevant long-term memories]
  + [Last 3 summaries]
  + [Last 50 messages]
  = Full unlimited context passed to LLM
```

### ReAct Agent Loop

```
User input
    ↓
Build context (all memory tiers)
    ↓
LLM reasons + decides tool calls
    ↓
Execute tools (bash/web/kali/ssh/etc.)
    ↓
Feed results back to LLM
    ↓
Repeat (up to 8 iterations)
    ↓
Final Okabe-flavored response
```

---

## Recommended Improvements

Once running, consider these free enhancements:

1. **Cloudflare Tunnel** — Expose MirAI to internet without port forwarding (free)
2. **Ngrok** — Instant public URL for your Legion Go (free tier)
3. **Groq API** — Fastest free LLM inference (add as 5th provider)
4. **Together.ai** — Additional free LLM tier for load balancing
5. **Tavily API** — Better web search than DuckDuckGo (free tier: 1000 searches/month)
6. **Mem0** — Cloud memory persistence (free tier available)
7. **Notdiamond** — Automatic routing between free LLM models
8. **Qdrant Cloud** — Managed vector store if ChromaDB needs scaling (free 1GB)

---

## Security Notes

- Telegram bot only responds to admin user IDs in `TELEGRAM_ADMIN_IDS`
- Kali tools have full system access — only grant access to trusted users
- SSH keys are stored at `~/.ssh/` with 600 permissions
- `.env` is gitignored — never commit it
- For public deployment: use Cloudflare Tunnel + additional auth

---

```
El Psy Kongroo.
— Hououin Kyouma, Future Gadget Lab #8
```