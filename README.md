# MirAI_OS

Advanced AI Operating System – runs on **Kali Linux / WSL2** (Legion Go).  
One-command container stack: Ollama · N8n · Flowise · LangChain · Kali · Rancher · and more.

---

## 🚀 Quick Start

### Windows (WSL2 / Kali)
```bat
install.bat          ← batch installer (run as Administrator)
install.ps1          ← PowerShell installer (alternative)
start.bat            ← start the stack
```

### Linux / Kali
```bash
chmod +x install.sh && ./install.sh
```

---

## 🐳 Container Stack

| Container | Description | Port |
|---|---|---|
| **Agentverse** | Next.js + Ollama chat UI | 3000 |
| **Ollama** | Local LLM runtime (Nous-Hermes-2-Mistral-7B-DPO) | 11434 |
| **N8n** | Workflow automation | 5678 |
| **Flowise** | Visual LLM/agent builder | 3001 |
| **LangChain** | Rolling context API + sentence-transformer embeddings | 8100 |
| **ChromaDB** | Vector database | 8000 |
| **Context Storage** | PostgreSQL + pgvector (128 GB optimised) | 5432 |
| **Redis** | Cache + pub/sub | 6379 |
| **Orchestrator** | MirAI core (Mod 2, Nous-Hermes, persona routing) | 8080 |
| **CSM** | Sesame AI speech synthesis | 8300 |
| **Whisper** | faster-whisper-plus STT | 8400 |
| **Kali Linux** | nmap · nuclei · dirbuster · XFCE · DinD (VNC/noVNC) | 5901/6901 |
| **Rancher** | Multi-VM SSH orchestration / Kubernetes management | 9090/9443 |
| **OpenClaw** | Game-agent sandbox | 8200 |
| **PC Control** | pynput full desktop control API | 8500 |
| **Robin** | Tor dark-web proxy | 9050 |
| **D-Drive Storage** | MinIO 256 GB object store on D:\ | 9000/9001 |
| **Swap Manager** | 256 GB SSD→RAM swap (privileged) | — |
| **Nginx** | TLS reverse proxy / security gateway | 80/443 |

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and set your keys:
```ini
OLLAMA_MODEL=nous-hermes-2-mistral-7b-dpo
OPENROUTER_API_KEY=<optional>
TELEGRAM_BOT_TOKEN=<optional>
```

WSL2 memory/swap: copy `wslconfig.template` to `%USERPROFILE%\.wslconfig`.

---

## 🐍 Direct Python Usage (without Docker)

```bash
pip install -r requirements.txt
python main.py --mode cli         # interactive CLI
python main.py --mode telegram    # Telegram bot
```

---

## 🔌 Mod System (Mod 2)

Drop Python files into `mods/` – no restart needed:
```python
# mods/my_mod.py
MOD_NAME    = "my_skill"
MOD_VERSION = "1.0.0"

def setup(bot, llm, ctx): ...
def on_startup(ctx): ...          # Mod 2
def on_shutdown(ctx): ...         # Mod 2
def on_message(message, ctx):
    if message == "ping":
        return "pong"
    return None
```

Hot-reload: `POST /mods/reload/{mod_name}` on the orchestrator API.

---

## 📦 Building .exe

```bash
python build_installer.py
# → dist/MirAI_OS.exe  (Windows)  or  dist/MirAI_OS  (Linux)
```

## 🧪 Smoke Test
```bash
python smoke_test.py
python smoke_test.py --exe dist/MirAI_OS.exe
```

---

## Contributing
Feel free to open issues and submit pull requests!