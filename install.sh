#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
#  MirAI_OS  –  Linux / WSL2 (Kali) Installer
#  Supports: Kali Linux · Ubuntu · Debian · WSL2
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${REPO_DIR}/install.log"

_log()  { echo -e "\033[1;32m[MirAI]\033[0m $*" | tee -a "${LOG_FILE}"; }
_warn() { echo -e "\033[1;33m[WARN]\033[0m  $*" | tee -a "${LOG_FILE}"; }
_err()  { echo -e "\033[1;31m[ERROR]\033[0m $*" | tee -a "${LOG_FILE}"; exit 1; }

_log "MirAI_OS installer  –  $(date)"
_log "Working directory: ${REPO_DIR}"

# ─── Detect environment ────────────────────────────────────────────────────────
IS_WSL=false
if grep -qiE "microsoft|wsl" /proc/version 2>/dev/null; then
    IS_WSL=true
    _log "WSL2 detected"
fi

OS_ID="$(grep -oP '(?<=^ID=).+' /etc/os-release 2>/dev/null | tr -d '"' || echo unknown)"
_log "OS: ${OS_ID}"

# ─── System dependencies ──────────────────────────────────────────────────────
_log "Installing system packages…"
if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv \
        curl wget git \
        portaudio19-dev \
        libxcb1 libx11-dev \
        ca-certificates \
        gnupg \
        lsb-release \
        2>/dev/null || _warn "Some packages failed; continuing"
fi

# ─── Docker ───────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    _log "Installing Docker…"
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "${USER}" || true
    _log "Docker installed. You may need to log out and back in for group changes."
else
    _log "Docker already installed: $(docker --version)"
fi

# ─── Docker Compose v2 ────────────────────────────────────────────────────────
if ! docker compose version &>/dev/null 2>&1; then
    _log "Installing Docker Compose plugin…"
    COMPOSE_VERSION="v2.29.0"
    ARCH="$(uname -m)"
    sudo mkdir -p /usr/local/lib/docker/cli-plugins
    sudo curl -SL \
        "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-${ARCH}" \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    _log "Docker Compose installed."
else
    _log "Docker Compose already installed: $(docker compose version)"
fi

# ─── Python virtual environment ───────────────────────────────────────────────
_log "Setting up Python virtual environment…"
if [ ! -d "${REPO_DIR}/.venv" ]; then
    python3 -m venv "${REPO_DIR}/.venv"
fi
# shellcheck disable=SC1091
source "${REPO_DIR}/.venv/bin/activate"

pip install --upgrade pip -q
pip install -r "${REPO_DIR}/requirements.txt" -q || \
    _warn "Some Python packages failed (PyAudio is optional)"

# ─── Environment file ─────────────────────────────────────────────────────────
if [ ! -f "${REPO_DIR}/.env" ]; then
    _log "Creating .env from template…"
    cp "${REPO_DIR}/.env.example" "${REPO_DIR}/.env"
    _warn "Edit ${REPO_DIR}/.env and set your API keys before starting."
fi

# ─── WSL2: .wslconfig guidance ────────────────────────────────────────────────
if "${IS_WSL}"; then
    WIN_HOME="$(wslpath "$(cmd.exe /C "echo %USERPROFILE%" 2>/dev/null | tr -d '\r')" 2>/dev/null || echo "")"
    WSLCFG="${WIN_HOME}/.wslconfig"
    if [ -n "${WIN_HOME}" ] && [ ! -f "${WSLCFG}" ]; then
        _log "Copying .wslconfig template to Windows home…"
        cp "${REPO_DIR}/wslconfig.template" "${WSLCFG}" 2>/dev/null || \
            _warn "Could not copy .wslconfig – copy wslconfig.template manually to %USERPROFILE%\\.wslconfig"
    fi
fi

# ─── D-Drive storage directory ────────────────────────────────────────────────
D_PATH="${D_DRIVE_PATH:-/mnt/d/mirai_storage}"
if "${IS_WSL}" && [ -d "/mnt/d" ]; then
    mkdir -p "${D_PATH}" 2>/dev/null || _warn "Could not create ${D_PATH}"
    mkdir -p "/mnt/d/mirai_swap"   2>/dev/null || true
    _log "D-drive storage path: ${D_PATH}"
fi

# ─── Pull & start containers ──────────────────────────────────────────────────
_log "Pulling Docker images (this may take a while)…"
cd "${REPO_DIR}"
docker compose pull --quiet 2>/dev/null || _warn "Some images couldn't be pulled"

_log "Building custom containers…"
docker compose build --parallel 2>&1 | tee -a "${LOG_FILE}" || \
    _warn "Some containers failed to build; check ${LOG_FILE}"

_log "Starting MirAI_OS stack…"
docker compose up -d

# Wait for orchestrator health
_log "Waiting for orchestrator to become ready…"
for i in $(seq 1 30); do
    if curl -sf http://localhost:8080/health &>/dev/null; then
        _log "Orchestrator is healthy."
        break
    fi
    sleep 5
done

# ─── Summary ──────────────────────────────────────────────────────────────────
cat <<'EOF'

┌─────────────────────────────────────────────────────────────────────────────┐
│  MirAI_OS is running!                                                       │
│                                                                             │
│  Service          URL                                                       │
│  ───────────────  ──────────────────────────────────────────────────────   │
│  Agentverse UI    https://localhost    (Nginx → :3000)                      │
│  Orchestrator     http://localhost:8080                                     │
│  N8n              http://localhost:5678                                     │
│  Flowise          http://localhost:3001                                     │
│  Rancher          https://localhost:9443                                    │
│  Kali VNC         localhost:5901  (noVNC: http://localhost:6901)            │
│  D-Drive MinIO    http://localhost:9001                                     │
│  Whisper STT      http://localhost:8400                                     │
│  CSM TTS          http://localhost:8300                                     │
│  Robin (Tor)      socks5://localhost:9050                                   │
│                                                                             │
│  CLI mode:        python main.py --mode cli                                 │
│  Telegram bot:    python main.py --mode telegram                            │
│                                                                             │
│  Logs:            docker compose logs -f                                    │
│  Stop:            docker compose down                                       │
└─────────────────────────────────────────────────────────────────────────────┘

EOF
