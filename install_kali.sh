#!/usr/bin/env bash
# =============================================================================
# MirAI_OS – Kali Linux / WSL2 Full Installer
# =============================================================================
# Installs:
#   • System dependencies (Python 3.11+, pip, audio libs, git, curl)
#   • Ollama with dolphin-llama3:8b (uncensored 8B model)
#   • Full Kali Linux toolset (200+ tools via kali-linux-default + extras)
#   • MirAI_OS Python requirements
#   • Systemd service for 24/7 game engine
#
# Supports: Kali Linux, Debian/Ubuntu, Fedora/RHEL, Arch, WSL2
#
# Usage:
#   chmod +x install_kali.sh && sudo bash install_kali.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/install.log"
OLLAMA_MODEL="${OLLAMA_MODEL:-dolphin-llama3:8b}"
MIRAI_USER="${SUDO_USER:-$(whoami)}"

# ── Color helpers ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
success() { echo -e "${GREEN}[OK]${NC}    $*" | tee -a "$LOG_FILE"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"; }
step()    { echo -e "\n${BLUE}━━━ $* ━━━${NC}" | tee -a "$LOG_FILE"; }

# ── Detect OS ──────────────────────────────────────────────────────────────
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_ID="${ID:-unknown}"
        OS_LIKE="${ID_LIKE:-}"
    else
        OS_ID="unknown"
        OS_LIKE=""
    fi

    if echo "$OS_ID $OS_LIKE" | grep -qiE "kali|debian|ubuntu|mint|pop"; then
        PKG_MGR="apt"
    elif echo "$OS_ID $OS_LIKE" | grep -qiE "fedora|rhel|centos|rocky|alma"; then
        PKG_MGR="dnf"
    elif echo "$OS_ID" | grep -qiE "arch|manjaro|endeavour"; then
        PKG_MGR="pacman"
    else
        PKG_MGR="apt"   # fallback
        warn "Unknown OS ($OS_ID). Assuming apt."
    fi
    info "Detected OS: $OS_ID (package manager: $PKG_MGR)"
}

# ── Check WSL ──────────────────────────────────────────────────────────────
is_wsl() {
    grep -qiE "microsoft|wsl" /proc/version 2>/dev/null
}

# ── Package installer ──────────────────────────────────────────────────────
pkg_install() {
    case "$PKG_MGR" in
        apt)    DEBIAN_FRONTEND=noninteractive apt-get install -y "$@" >> "$LOG_FILE" 2>&1 ;;
        dnf)    dnf install -y "$@" >> "$LOG_FILE" 2>&1 ;;
        pacman) pacman -S --noconfirm "$@" >> "$LOG_FILE" 2>&1 ;;
    esac
}

pkg_update() {
    case "$PKG_MGR" in
        apt)    apt-get update -y >> "$LOG_FILE" 2>&1 ;;
        dnf)    dnf check-update -y >> "$LOG_FILE" 2>&1 || true ;;
        pacman) pacman -Sy >> "$LOG_FILE" 2>&1 ;;
    esac
}

# ── Step 0: Banner ─────────────────────────────────────────────────────────
echo -e "${CYAN}"
cat << 'BANNER'
  __  __ _      _    _    ___  ____
 |  \/  (_)_ _ / \  (_)  / _ \/ ___|
 | |\/| | | '_/ _ \ | | | | | \___ \
 | |  | | | |/ ___ \| | | |_| |___) |
 |_|  |_|_|_/_/   \_|_|  \___/|____/
  El Psy Kongroo — Kali Linux Installer
BANNER
echo -e "${NC}"

# ── Root check ─────────────────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    error "Run with sudo: sudo bash install_kali.sh"
    exit 1
fi

# ── Init log ───────────────────────────────────────────────────────────────
mkdir -p "$SCRIPT_DIR"
echo "=== MirAI_OS Install Log $(date) ===" > "$LOG_FILE"

detect_os

# ═══ STEP 1 – System update ════════════════════════════════════════════════
step "System Update"
pkg_update && success "Package list updated."

# ═══ STEP 2 – Core dependencies ════════════════════════════════════════════
step "Core Dependencies"
CORE_PKGS=(
    curl wget git build-essential
    python3 python3-pip python3-venv python3-dev
    libssl-dev libffi-dev
    portaudio19-dev libespeak-ng1 ffmpeg
    jq unzip net-tools
)

if [ "$PKG_MGR" = "dnf" ]; then
    CORE_PKGS=(
        curl wget git gcc gcc-c++ make
        python3 python3-pip python3-devel
        openssl-devel libffi-devel
        portaudio-devel espeak-ng ffmpeg
        jq unzip net-tools
    )
elif [ "$PKG_MGR" = "pacman" ]; then
    CORE_PKGS=(
        curl wget git base-devel
        python python-pip
        openssl libffi
        portaudio espeak-ng ffmpeg
        jq unzip net-tools
    )
fi

pkg_install "${CORE_PKGS[@]}" && success "Core packages installed."

# ═══ STEP 3 – Kali Linux Tools ═════════════════════════════════════════════
step "Kali Linux Security Tools"

if [ "$OS_ID" = "kali" ]; then
    info "Kali Linux detected – installing full toolset…"

    # Meta-packages
    KALI_META=(
        kali-linux-default
        kali-tools-web
        kali-tools-wireless
        kali-tools-exploitation
        kali-tools-forensics
        kali-tools-sniffing-spoofing
        kali-tools-passwords
        kali-tools-reporting
        kali-tools-reverse-engineering
        kali-tools-social-engineering
    )

    for meta in "${KALI_META[@]}"; do
        info "Installing $meta…"
        DEBIAN_FRONTEND=noninteractive apt-get install -y "$meta" >> "$LOG_FILE" 2>&1 && \
            success "$meta installed." || warn "$meta failed (may need manual install)."
    done
else
    info "Non-Kali system – installing individual security tools…"

    # Individual tools available on Debian/Ubuntu
    SEC_TOOLS=(
        nmap masscan nikto sqlmap hydra john
        aircrack-ng reaver pixiewps
        metasploit-framework
        wireshark tcpdump tshark
        netcat-traditional ncat socat
        gobuster ffuf dirb wfuzz
        hashcat hashid hash-identifier
        steghide stegseek
        whatweb wafw00f
        exploitdb
        burpsuite
        beef-xss
        maltego
        theharvester recon-ng
        mimikatz
        responder
        impacket-scripts
        crackmapexec
        enum4linux
        smbclient smbmap
        dnsutils dnsrecon
        whois
        proxychains4
        tor torsocks
        netdiscover arp-scan
        macchanger
        openvpn wireguard
        docker.io docker-compose
        tmux screen
        vim neovim
        zsh
        python3-scapy python3-impacket
        python3-requests python3-paramiko python3-cryptography
    )

    for tool in "${SEC_TOOLS[@]}"; do
        pkg_install "$tool" >> "$LOG_FILE" 2>&1 && \
            success "$tool ✓" || warn "$tool – skipped (not available in repos)."
    done
fi

# ═══ STEP 4 – Docker (if not Kali) ═════════════════════════════════════════
step "Docker Setup"
if ! command -v docker &>/dev/null; then
    if [ "$PKG_MGR" = "apt" ]; then
        curl -fsSL https://get.docker.com | bash >> "$LOG_FILE" 2>&1 && success "Docker installed."
        usermod -aG docker "$MIRAI_USER" 2>/dev/null || true
    fi
else
    success "Docker already installed."
fi

# ═══ STEP 5 – Ollama (local 8B uncensored model) ═══════════════════════════
step "Ollama – Local LLM Backend"

if ! command -v ollama &>/dev/null; then
    info "Downloading and installing Ollama…"
    curl -fsSL https://ollama.com/install.sh | sh >> "$LOG_FILE" 2>&1 && \
        success "Ollama installed."
else
    success "Ollama already installed ($(ollama --version 2>/dev/null | head -1))."
fi

# Start Ollama in background if not running
if ! pgrep -x ollama &>/dev/null; then
    info "Starting Ollama service…"
    if is_wsl; then
        # WSL2: start in background without systemd
        nohup ollama serve >> "$LOG_FILE" 2>&1 &
        sleep 3
    else
        systemctl enable --now ollama 2>/dev/null || \
            { nohup ollama serve >> "$LOG_FILE" 2>&1 & sleep 3; }
    fi
fi

# Pull the uncensored 8B model
info "Pulling model: $OLLAMA_MODEL (uncensored 8B)…"
info "This may take several minutes depending on your connection…"
if ollama pull "$OLLAMA_MODEL" >> "$LOG_FILE" 2>&1; then
    success "Model $OLLAMA_MODEL ready."
else
    warn "Model pull failed. Run manually: ollama pull $OLLAMA_MODEL"
fi

# Pull fallback model
FALLBACK_MODEL="llama3:8b"
info "Pulling fallback model: $FALLBACK_MODEL…"
ollama pull "$FALLBACK_MODEL" >> "$LOG_FILE" 2>&1 && \
    success "Fallback model $FALLBACK_MODEL ready." || \
    warn "Fallback model pull failed. Run: ollama pull $FALLBACK_MODEL"

# ═══ STEP 6 – Python virtual environment ═══════════════════════════════════
step "Python Virtual Environment"

VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR" >> "$LOG_FILE" 2>&1 && success "Virtual environment created."
fi

source "$VENV_DIR/bin/activate"

# Upgrade pip inside venv
pip install --upgrade pip >> "$LOG_FILE" 2>&1

# ═══ STEP 7 – Python dependencies ══════════════════════════════════════════
step "Python Dependencies"

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    pip install -r "$SCRIPT_DIR/requirements.txt" >> "$LOG_FILE" 2>&1 && \
        success "Python dependencies installed."
else
    warn "requirements.txt not found. Installing core packages only."
    pip install httpx python-dotenv python-telegram-bot >> "$LOG_FILE" 2>&1
fi

# ═══ STEP 8 – Environment configuration ════════════════════════════════════
step "Environment Configuration"

ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

if [ ! -f "$ENV_FILE" ] && [ -f "$ENV_EXAMPLE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    success ".env created from .env.example"
elif [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << EOF
# MirAI_OS Environment Configuration
# Generated by install_kali.sh on $(date)

# === LLM Settings ===
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=${OLLAMA_MODEL}

# === API Keys (optional) ===
OPENROUTER_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_ID=

# === Features ===
WSL_ENABLED=true
KALI_ENABLED=true
VOICE_ENABLED=false
LOG_LEVEL=INFO
EOF
    success ".env created with defaults."
fi
chmod 600 "$ENV_FILE"

# ═══ STEP 9 – Directories ══════════════════════════════════════════════════
step "Data Directories"
mkdir -p "$SCRIPT_DIR/data" "$SCRIPT_DIR/logs"
chown -R "$MIRAI_USER":"$MIRAI_USER" "$SCRIPT_DIR/data" "$SCRIPT_DIR/logs" 2>/dev/null || true
success "Directories created."

# ═══ STEP 10 – Systemd service (non-WSL) ═══════════════════════════════════
step "MirAI_OS Service"

if ! is_wsl && command -v systemctl &>/dev/null; then
    SERVICE_FILE="/etc/systemd/system/mirai-os.service"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=MirAI_OS – AI Orchestrator with 303-Character Game
After=network.target ollama.service

[Service]
Type=simple
User=$MIRAI_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$VENV_DIR/bin/python $SCRIPT_DIR/main.py
Restart=on-failure
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable mirai-os 2>/dev/null || true
    success "Systemd service 'mirai-os' installed (not started – run: systemctl start mirai-os)."
else
    # WSL2 / no systemd: create a start script
    START_SCRIPT="$SCRIPT_DIR/start.sh"
    cat > "$START_SCRIPT" << EOF
#!/usr/bin/env bash
# Start MirAI_OS (WSL2 / non-systemd)
cd "$(dirname "\$0")"
source .venv/bin/activate

# Start Ollama if not running
pgrep -x ollama || (nohup ollama serve > logs/ollama.log 2>&1 &)
sleep 2

# Start MirAI_OS
python main.py "\$@"
EOF
    chmod +x "$START_SCRIPT"
    chown "$MIRAI_USER":"$MIRAI_USER" "$START_SCRIPT" 2>/dev/null || true
    success "Start script created: ./start.sh"
fi

# ═══ STEP 11 – WSL2 tweaks ═════════════════════════════════════════════════
if is_wsl; then
    step "WSL2 Optimizations"
    WSLCONF="/etc/wsl.conf"
    if [ ! -f "$WSLCONF" ]; then
        # Enable systemd if WSL version supports it (WSL 0.67.6+)
        # Detect if systemd is available
        SYSTEMD_LINE=""
        if wsl.exe --version 2>/dev/null | grep -q "WSL version"; then
            SYSTEMD_LINE=$'\n[boot]\nsystemd=true'
        fi
        cat > "$WSLCONF" << EOF
[network]
generateResolvConf=true
${SYSTEMD_LINE}
[interop]
enabled=true
appendWindowsPath=false
EOF
        success "/etc/wsl.conf created."
    fi

    # Optional: increase memory available to WSL2 by creating .wslconfig hint
    WSLCONFIG_HINT="$SCRIPT_DIR/wslconfig_hint.txt"
    cat > "$WSLCONFIG_HINT" << 'EOF'
# Add these lines to %USERPROFILE%\.wslconfig on Windows to allocate more RAM:
[wsl2]
memory=16GB
processors=8
swap=8GB
localhostForwarding=true
EOF
    success "WSL2 config hint written to wslconfig_hint.txt"
fi

# ══════════════════════════════════════════════════════════════════════════ #
# Final summary                                                              #
# ══════════════════════════════════════════════════════════════════════════ #
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   MirAI_OS installation complete! 🎉       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
info "Installed model : $OLLAMA_MODEL (uncensored 8B)"
info "Python venv     : $VENV_DIR"
info "Config file     : $ENV_FILE"
info "Log file        : $LOG_FILE"
echo ""
echo -e "${CYAN}To start MirAI_OS:${NC}"
if is_wsl; then
    echo "  ./start.sh             # interactive CLI"
    echo "  ./start.sh --telegram  # Telegram bot mode"
else
    echo "  systemctl start mirai-os    # as a service"
    echo "  # or:"
    echo "  source .venv/bin/activate && python main.py"
fi
echo ""
echo -e "${YELLOW}Edit .env to set TELEGRAM_BOT_TOKEN and other credentials.${NC}"
echo -e "${CYAN}El Psy Kongroo. 🧪${NC}"
