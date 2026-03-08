#!/usr/bin/env bash
# ============================================================
#  MirAI_OS – Linux / WSL2 Installer
#  Usage: bash install.sh [--model <ollama-model>] [--skip-docker]
# ============================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OLLAMA_MODEL="${OLLAMA_MODEL:-dolphin-mistral}"
SKIP_DOCKER=false
COMPOSE_CMD=""

# ── Parse arguments ──────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)       OLLAMA_MODEL="$2"; shift 2 ;;
        --skip-docker) SKIP_DOCKER=true;  shift   ;;
        --help|-h)
            echo "Usage: bash install.sh [--model <ollama-model>] [--skip-docker]"
            echo ""
            echo "Options:"
            echo "  --model <name>   Ollama model to pull (default: dolphin-mistral)"
            echo "  --skip-docker    Skip Docker installation (if already installed)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────
info()    { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
success() { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()    { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
error()   { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; exit 1; }

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || error "'$1' is required but not installed."
}

# ── Step 1: OS detection ──────────────────────────────────────
info "Detecting operating system…"
if grep -qi microsoft /proc/version 2>/dev/null; then
    OS_TYPE="wsl2"
    info "Running inside WSL2"
elif [[ "$(uname -s)" == "Linux" ]]; then
    OS_TYPE="linux"
    info "Running on Linux"
else
    error "Unsupported OS. Use install.bat or install.ps1 on Windows."
fi

# ── Step 2: Install system dependencies ──────────────────────
info "Installing system dependencies…"
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends \
        curl wget git ca-certificates gnupg lsb-release
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y curl wget git ca-certificates gnupg
elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm curl wget git ca-certificates gnupg
else
    warn "Package manager not detected. Ensure curl, git, and wget are installed."
fi
success "System dependencies ready."

# ── Step 3: Install Docker ────────────────────────────────────
if [[ "$SKIP_DOCKER" == "true" ]]; then
    info "Skipping Docker installation (--skip-docker)."
elif command -v docker >/dev/null 2>&1; then
    success "Docker is already installed: $(docker --version)"
else
    info "Installing Docker…"
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "${USER}" || true
    success "Docker installed."

    if [[ "$OS_TYPE" == "linux" ]]; then
        sudo systemctl enable --now docker || true
    fi
fi

# ── Step 4: Ensure Docker Compose (v2 plugin) ────────────────
info "Checking Docker Compose…"
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
    success "Docker Compose v2 available."
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
    success "docker-compose (v1) found."
else
    info "Installing Docker Compose plugin…"
    DOCKER_CONFIG="${DOCKER_CONFIG:-$HOME/.docker}"
    mkdir -p "$DOCKER_CONFIG/cli-plugins"
    COMPOSE_VER="$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name"' | cut -d'"' -f4)"
    curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VER}/docker-compose-linux-$(uname -m)" \
        -o "$DOCKER_CONFIG/cli-plugins/docker-compose"
    chmod +x "$DOCKER_CONFIG/cli-plugins/docker-compose"
    COMPOSE_CMD="docker compose"
    success "Docker Compose installed (${COMPOSE_VER})."
fi

# ── Step 5: Create .env if missing ───────────────────────────
info "Setting up environment configuration…"
cd "$REPO_DIR"

if [[ ! -f .env ]]; then
    cp .env.example .env
    info ".env created from .env.example"
    info "Edit .env to add your TELEGRAM_TOKEN and OPENROUTER_API_KEY if needed."
fi

# Inject selected model into .env
if grep -q "^OLLAMA_MODEL=" .env 2>/dev/null; then
    sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=${OLLAMA_MODEL}|" .env
else
    echo "OLLAMA_MODEL=${OLLAMA_MODEL}" >> .env
fi
success "OLLAMA_MODEL set to '${OLLAMA_MODEL}' in .env"

# ── Step 6: Build and start containers ───────────────────────
info "Building Docker images…"
$COMPOSE_CMD build

info "Starting core services (postgres, redis, ollama)…"
$COMPOSE_CMD up -d postgres redis ollama

# ── Step 7: Wait for Ollama to be healthy ────────────────────
info "Waiting for Ollama to be ready (this may take 1-2 minutes on first run)…"
RETRIES=30
for i in $(seq 1 $RETRIES); do
    if docker exec mirai_ollama curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        success "Ollama is ready!"
        break
    fi
    if [[ $i -eq $RETRIES ]]; then
        error "Ollama did not become healthy after ${RETRIES} retries. Check: docker logs mirai_ollama"
    fi
    echo -n "."
    sleep 5
done

# ── Step 8: Pull the LLM model ───────────────────────────────
info "Pulling LLM model '${OLLAMA_MODEL}' into Ollama…"
info "(First pull may take several minutes depending on model size and internet speed)"
if docker exec mirai_ollama ollama pull "${OLLAMA_MODEL}"; then
    success "Model '${OLLAMA_MODEL}' pulled successfully!"
else
    error "Failed to pull model '${OLLAMA_MODEL}'. Check your internet connection or try a different model with --model."
fi

# ── Step 9: Start remaining services ────────────────────────
info "Starting all remaining services…"
$COMPOSE_CMD up -d

success "All services started!"

# ── Step 10: Health summary ───────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════"
echo "  MirAI_OS is running!"
echo "══════════════════════════════════════════════════════"
echo ""
echo "  Services:"
$COMPOSE_CMD ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || $COMPOSE_CMD ps
echo ""
echo "  Endpoints:"
echo "    Orchestrator API  →  http://localhost:8080"
echo "    Ollama (LLM)      →  http://localhost:11434"
echo "    N8n automation    →  http://localhost:5678"
echo "    Flowise builder   →  http://localhost:3001"
echo "    Nginx gateway     →  http://localhost:80"
echo "    PostgreSQL        →  localhost:5432"
echo "    Redis             →  localhost:6379"
echo "    ChromaDB          →  http://localhost:8000"
echo ""
echo "  Quick test:"
echo "    curl http://localhost:8080/health"
echo ""
echo "  To stop:   $COMPOSE_CMD down"
echo "  To view logs: $COMPOSE_CMD logs -f"
echo ""
echo "El Psy Kongroo."
