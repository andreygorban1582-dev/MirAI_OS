#!/usr/bin/env bash
# =============================================================================
# install.sh – MirAI_OS one-command Codespace / Linux installer
# =============================================================================
# Installs Python dependencies, the Ollama runtime, and pulls the
# Dolphin-Mistral (4B) model so the project is ready to run.
#
# Usage:
#   bash install.sh          # full install (deps + Ollama + model)
#   bash install.sh --deps   # Python deps only
# =============================================================================
set -euo pipefail

OLLAMA_MODEL="${OLLAMA_MODEL:-dolphin-mistral}"

# ---- helpers ----------------------------------------------------------------
info()  { printf '\033[1;34m[MirAI]\033[0m %s\n' "$*"; }
ok()    { printf '\033[1;32m[MirAI]\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m[MirAI]\033[0m %s\n' "$*"; }
error() { printf '\033[1;31m[MirAI]\033[0m %s\n' "$*" >&2; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# ---- 1. Python dependencies ------------------------------------------------
info "Installing Python dependencies …"
pip install --upgrade pip > /dev/null
pip install -r requirements.txt
ok "Python dependencies installed."

if [[ "${1:-}" == "--deps" ]]; then
    ok "Done (deps only)."
    exit 0
fi

# ---- 2. Ollama runtime -----------------------------------------------------
if command -v ollama &> /dev/null; then
    info "Ollama already installed – $(ollama --version 2>&1 || true)"
else
    info "Installing Ollama …"
    curl -fsSL https://ollama.com/install.sh | sh
    ok "Ollama installed."
fi

# ---- 3. Start Ollama server (if not already running) ------------------------
if ! curl -sf http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
    info "Starting Ollama server in the background …"
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    # Wait for the server to become ready
    for i in $(seq 1 30); do
        if curl -sf http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    if ! curl -sf http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
        error "Ollama server failed to start.  Check /tmp/ollama.log"
        exit 1
    fi
    ok "Ollama server running."
else
    info "Ollama server already running."
fi

# ---- 4. Pull model ---------------------------------------------------------
info "Pulling model '${OLLAMA_MODEL}' (this may take a few minutes) …"
ollama pull "$OLLAMA_MODEL"
ok "Model '${OLLAMA_MODEL}' ready."

# ---- 5. Write default .env (if not present) ---------------------------------
if [[ ! -f "$REPO_ROOT/.env" ]]; then
    info "Creating default .env …"
    cat > "$REPO_ROOT/.env" << 'ENVEOF'
# MirAI_OS environment — edit as needed
USE_OLLAMA=true
OLLAMA_MODEL=dolphin-mistral
# USE_LOCAL_LLM=false
# OPENROUTER_API_KEY=
# TELEGRAM_BOT_TOKEN=
ENVEOF
    ok ".env created."
else
    info ".env already exists – skipping."
fi

# ---- done -------------------------------------------------------------------
echo ""
ok "=========================================="
ok "  MirAI_OS installation complete!"
ok "=========================================="
echo ""
info "To start the CLI:      python main.py --mode cli"
info "To start Telegram bot: python main.py --mode telegram"
echo ""
