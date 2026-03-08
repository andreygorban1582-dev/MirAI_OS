# MirAI_OS

MirAI_OS is an advanced artificial intelligence operating system designed to integrate various functionalities such as communication, autonomous operations, and more.

## Features
- 💬 **Telegram Bot** with Okabe Rintaro personality (Steins;Gate)
- 🧠 **LLM Engine** with OpenRouter integration (streaming, retries, context trimming)
- 🎙 **Voice I/O** with Sesame CSM (TTS) and Whisper (STT)
- 🤖 **Autonomous Agent Flows** (ReAct: Reason + Act, multi-step tasks)
- 🔧 **Self-Modification System** (AST-validated, backed up before applying)
- 💀 **Kali Linux Integration** via SSH (with dangerous-command blocking)
- 🔌 **Codespace SSH Connector**
- ⚡ **Context Optimizer** — dynamically adjusts token budget based on live RAM/VRAM pressure
- 🎮 **Legion Go Optimizer** — AMD ROCm/HIP environment setup, CPU thread tuning, TF32 PyTorch
- 🧪 **Lab** — Gradio web UI with 10 tabs: Chat, Agent, Voice I/O, Hardware Monitor, Code Sandbox, Prompt Engineering, Model Comparison, Self-Modification, Kali Console, Codespace SSH
- 📦 **Windows .exe Installer** (PyInstaller)

## Legion Go Optimisations

MirAI_OS is specifically tuned for the **Lenovo Legion Go** (AMD Ryzen Z1 Extreme + Radeon 780M, 16 GB RAM):

| Setting | Value |
|---------|-------|
| Context window | 4096 tokens (dynamic, scales with RAM pressure) |
| Quantisation | Q4_K_M |
| GPU layers | 20 (AMD Radeon 780M via ROCm) |
| CPU threads | 8 (all P-cores) |
| Batch size | 4 |
| TDP mode | Balanced (25 W) |

The `LegionGoOptimizer` sets the following at startup:
- `HIP_VISIBLE_DEVICES=0`, `ROCR_VISIBLE_DEVICES=0`
- `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS` = CPU cores − 2
- `MIOPEN_FIND_MODE=FAST` for faster kernel selection
- PyTorch TF32 enabled on ROCm device

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/andreygorban1582-dev/MirAI_OS.git
cd MirAI_OS

# 2. Install dependencies
pip install -r requirements.txt

# 3. For AMD ROCm (Legion Go):
pip install torch --index-url https://download.pytorch.org/whl/rocm5.7

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Run
python main.py           # Launch Lab web UI (default)
python main.py bot       # Start Telegram bot
python main.py chat      # Interactive CLI chat
python main.py agent "your task here"  # Autonomous agent
```

## Project Structure

```
MirAI_OS/
├── main.py                    # Entry point
├── requirements.txt
├── pytest.ini
├── .env.example
├── config/
│   ├── settings.py            # Pydantic settings
│   └── legion_go_profile.json # Legion Go hardware profile
├── core/
│   ├── llm_engine.py          # OpenRouter LLM client
│   ├── context_optimizer.py   # RAM/VRAM-aware context management
│   └── agent_flow.py          # ReAct autonomous agent
├── bot/
│   ├── telegram_bot.py        # Telegram bot
│   └── personality/
│       └── okabe.py           # Okabe Rintaro persona
├── voice/
│   └── voice_io.py            # STT (Whisper) + TTS (Sesame CSM)
├── lab/
│   └── lab_interface.py       # Gradio web UI (10 tabs)
├── system/
│   ├── legion_go_optimizer.py # AMD ROCm + thread optimisations
│   ├── self_modification.py   # AST-safe code patching
│   ├── kali_integration.py    # SSH → Kali Linux
│   └── codespace_ssh.py       # GitHub Codespace SSH
├── installer/
│   └── build_exe.py           # Windows PyInstaller build
└── tests/
    ├── test_context_optimizer.py
    ├── test_llm_engine.py
    ├── test_agent_flow.py
    ├── test_personality.py
    └── test_system.py
```

## Lab

Launch the Lab with `python main.py` (or `python main.py lab`) and open [http://localhost:7860](http://localhost:7860).

| Tab | Description |
|-----|-------------|
| 💬 Chat | Multi-turn chat with MirAI |
| 🤖 Agent | Autonomous multi-step task runner |
| 🎙 Voice I/O | Microphone STT + Sesame CSM TTS |
| 🖥 Hardware Monitor | Live RAM/GPU stats + AI budget |
| 🐍 Code Sandbox | Execute Python in a local sandbox |
| ✍ Prompt Engineering | Craft & test system prompts |
| ⚖ Model Comparison | Side-by-side model responses |
| 🔧 Self-Modification | Instruct MirAI to patch its own code |
| 💀 Kali Console | Run commands on Kali Linux via SSH |
| 🔌 Codespace SSH | Run commands on GitHub Codespace |

## Configuration

Copy `.env.example` to `.env` and fill in:

```env
OPENROUTER_API_KEY=...
TELEGRAM_BOT_TOKEN=...
HUGGINGFACE_TOKEN=...
HARDWARE_PROFILE=legion_go   # or generic, high_end, low_end
```

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

## Contributing
Feel free to open issues and submit pull requests to contribute!
