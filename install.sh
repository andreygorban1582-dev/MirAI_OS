#!/usr/bin/env bash
# ============================================================
# MirAI_OS – Linux / WSL2 Installer
# Usage: bash install.sh
# ============================================================

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo ""
echo "============================================================"
echo "  MirAI_OS Installer v1.0.0"
echo "============================================================"
echo ""

# ── Python check ──────────────────────────────────────────────────────────────
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)
if [ -z "$PYTHON" ]; then
    echo "[ERROR] Python 3 not found."
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  Fedora:        sudo dnf install python3"
    exit 1
fi
PYVER=$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[OK] Python $PYVER"

# ── pip ───────────────────────────────────────────────────────────────────────
"$PYTHON" -m ensurepip --upgrade 2>/dev/null || true
"$PYTHON" -m pip install --upgrade pip --quiet
echo "[OK] pip ready"

# ── system audio libs (optional for voice) ───────────────────────────────────
if command -v apt-get &>/dev/null; then
    echo "[INFO] Installing system audio libraries (optional)..."
    sudo apt-get install -y --no-install-recommends \
        portaudio19-dev libespeak-ng1 ffmpeg 2>/dev/null || true
fi

# ── Python dependencies ───────────────────────────────────────────────────────
echo "[INFO] Installing Python dependencies..."
"$PYTHON" -m pip install -r requirements.txt --quiet
echo "[OK] Dependencies installed"

# ── Ollama ────────────────────────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
    echo "[INFO] Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "[OK] Ollama already installed"
fi

# ── Ollama model ─────────────────────────────────────────────────────────────
MODEL="${OLLAMA_MODEL:-dolphin-mistral}"
echo "[INFO] Pulling Ollama model '$MODEL' (this may take a few minutes)..."
ollama pull "$MODEL" || echo "[WARN] Could not pull model – ensure Ollama is running."

# ── .env ──────────────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || cat > .env <<'EOF'
# MirAI_OS environment – edit as needed
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_ID=
OPENROUTER_API_KEY=
OLLAMA_MODEL=dolphin-mistral
MOD2_ENABLED=true
VOICE_ENABLED=false
LOG_LEVEL=INFO
EOF
    echo "[OK] .env created (edit to add your API keys)"
fi

# ── data / log dirs ──────────────────────────────────────────────────────────
mkdir -p data logs

echo ""
echo "============================================================"
echo "  Installation complete!"
echo "  To start MirAI_OS:"
echo "    python3 main.py              # interactive CLI"
echo "    python3 main.py --mode service   # background services"
echo "    python3 main.py --mode telegram  # Telegram bot only"
echo "============================================================"
echo ""
