#!/bin/bash
# ============================================================
#  MirAI OS — WSL2 Kali Linux Optimization Script
#  Run this INSIDE your Kali WSL2 instance.
#  El Psy Kongroo.
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[FUTURE GADGET LAB]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
fail() { echo -e "${RED}[✗]${NC} $*"; exit 1; }

log "Initializing MirAI OS WSL2 setup for Legion Go..."
log "Z1 Extreme CPU | 16GB RAM | WSL2 Kali Linux"

# ── 1. System update ──────────────────────────────────────────────────────────
log "Updating system packages..."
sudo apt-get update -qq && sudo apt-get upgrade -y -qq
ok "System updated."

# ── 2. Install core dependencies ──────────────────────────────────────────────
log "Installing core dependencies..."
sudo apt-get install -y -qq \
    python3 python3-pip python3-venv python3-dev \
    git curl wget build-essential \
    ffmpeg espeak-ng \
    redis-server \
    sqlite3 \
    libssl-dev libffi-dev \
    chromium \
    tor \
    screen tmux \
    jq yq
ok "Core dependencies installed."

# ── 3. Install Kali pentesting tools ─────────────────────────────────────────
log "Installing/verifying Kali toolset..."
sudo apt-get install -y -qq \
    nmap \
    nikto \
    gobuster \
    sqlmap \
    hydra \
    john \
    hashcat \
    aircrack-ng \
    wireshark-common \
    tshark \
    tcpdump \
    netcat-traditional \
    binwalk \
    forensic-artifacts \
    wordlists \
    dirb \
    || warn "Some Kali tools may not be available in this distro variant."
ok "Kali tools installed."

# ── 4. Python virtual environment ────────────────────────────────────────────
MIRAI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
log "Setting up Python venv at $MIRAI_DIR/venv ..."
cd "$MIRAI_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
ok "Python environment ready."

# ── 5. Playwright browsers ───────────────────────────────────────────────────
log "Installing Playwright Chromium browser..."
python3 -m playwright install chromium --with-deps || warn "Playwright install may need --no-sandbox fix"
ok "Playwright ready."

# ── 6. Whisper model download ────────────────────────────────────────────────
log "Pre-downloading Whisper 'base' model (~145MB)..."
python3 -c "import whisper; whisper.load_model('base')" || warn "Whisper model download failed (will retry on first use)"
ok "Whisper model cached."

# ── 7. Redis auto-start ───────────────────────────────────────────────────────
log "Configuring Redis..."
sudo service redis-server start || true
echo "redis-server --daemonize yes" >> ~/.bashrc
ok "Redis configured."

# ── 8. Environment file ───────────────────────────────────────────────────────
if [ ! -f "$MIRAI_DIR/.env" ]; then
    cp "$MIRAI_DIR/config/.env.example" "$MIRAI_DIR/.env"
    warn ".env created from template. Edit it: nano $MIRAI_DIR/.env"
else
    ok ".env already exists."
fi

# ── 9. Auto-start on WSL boot ────────────────────────────────────────────────
log "Setting up auto-start..."
cat > ~/.mirai_start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/MirAI_OS" 2>/dev/null || cd ~/MirAI_OS
source venv/bin/activate 2>/dev/null || true
sudo service redis-server start 2>/dev/null || true
screen -dmS mirai python main.py
echo "[MirAI OS] Started in screen session 'mirai'"
EOF
chmod +x ~/.mirai_start.sh

# Add to .bashrc for WSL startup
if ! grep -q "mirai_start" ~/.bashrc; then
    echo "# MirAI OS auto-start" >> ~/.bashrc
    echo "# Uncomment next line to auto-start on WSL login:" >> ~/.bashrc
    echo "# bash ~/.mirai_start.sh" >> ~/.bashrc
fi
ok "Auto-start script created: ~/.mirai_start.sh"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  MirAI OS WSL2 Setup Complete!                 ║${NC}"
echo -e "${CYAN}╠════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║  Next steps:                                    ║${NC}"
echo -e "${CYAN}║  1. Edit .env:  nano $MIRAI_DIR/.env           ║${NC}"
echo -e "${CYAN}║  2. Setup swap: bash scripts/setup_swap.sh     ║${NC}"
echo -e "${CYAN}║  3. Run MirAI:  python main.py                 ║${NC}"
echo -e "${CYAN}║                                                 ║${NC}"
echo -e "${CYAN}║  El Psy Kongroo.                               ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"
