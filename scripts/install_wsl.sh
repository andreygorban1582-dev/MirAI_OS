#!/usr/bin/env bash
# =============================================================================
#  MirAI_OS  –  One-Shot Installer for Kali Linux (WSL2 or native)
#  Lenovo Legion Go Edition
# =============================================================================
#
#  WHAT THIS SCRIPT DOES
#  ─────────────────────
#  1. Checks prerequisites (Python ≥3.10, pip, git)
#  2. Updates the package manager and installs system-level dependencies
#     (build tools, audio libs, Tor, proxychains-ng, portaudio)
#  3. Clones or updates the MirAI_OS repository
#  4. Creates a Python virtual-environment and installs all Python packages
#  5. Copies .env.example → .env (if .env doesn't exist) and prompts for keys
#  6. Creates a workspace directory and systemd user service (optional)
#  7. Configures Tor and proxychains for anonymous operation
#  8. Verifies the installation by importing the mirai package
#
#  USAGE
#  ─────
#  curl -fsSL https://raw.githubusercontent.com/andreygorban1582-dev/MirAI_OS/main/scripts/install_wsl.sh | bash
#
#  Or clone first and run:
#    git clone https://github.com/andreygorban1582-dev/MirAI_OS.git
#    cd MirAI_OS
#    bash scripts/install_wsl.sh
#
#  TESTED ON
#  ─────────
#  • Kali Linux 2024.x in WSL2 (Windows 11 / Legion Go)
#  • Kali Linux 2024.x bare-metal
#
# =============================================================================

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[MirAI]${RESET} $*"; }
success() { echo -e "${GREEN}[✓]${RESET} $*"; }
warn()    { echo -e "${YELLOW}[!]${RESET} $*"; }
error()   { echo -e "${RED}[✗]${RESET} $*" >&2; exit 1; }

# ── Variables ─────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/andreygorban1582-dev/MirAI_OS.git"
INSTALL_DIR="${HOME}/MirAI_OS"
VENV_DIR="${INSTALL_DIR}/.venv"
DATA_DIR="${INSTALL_DIR}/data"
PYTHON_MIN_MINOR=10

# ── Banner ────────────────────────────────────────────────────────────────────
echo -e "${BOLD}${CYAN}"
cat << 'EOF'
  __  __ _       _    _    ___  ____
 |  \/  (_)_ __ / \  |_ _|/ _ \/ ___|
 | |\/| | | '__/ _ \  | || | | \___ \
 | |  | | | | / ___ \ | || |_| |___) |
 |_|  |_|_|_|/_/   \_\___|\___/|____/

  Autonomous AI Agent  ·  Kali Linux / WSL2
  Legion Go Edition
EOF
echo -e "${RESET}"
info "Starting installation…"
echo ""

# ── 1. Check OS ───────────────────────────────────────────────────────────────
if [[ "$(uname -s)" != "Linux" ]]; then
    error "This installer requires Linux (Kali / WSL2). Run it inside WSL2."
fi

# ── 2. Check Python version ───────────────────────────────────────────────────
info "Checking Python version…"
if ! command -v python3 &>/dev/null; then
    error "python3 not found. Install it with: sudo apt install python3"
fi
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if (( PY_MINOR < PYTHON_MIN_MINOR )); then
    error "Python 3.${PYTHON_MIN_MINOR}+ is required (found 3.${PY_MINOR})."
fi
success "Python 3.${PY_MINOR} found."

# ── 3. Update apt and install system packages ─────────────────────────────────
info "Updating package list and installing system dependencies…"
sudo apt-get update -qq

PACKAGES=(
    # Build tools
    build-essential python3-dev python3-pip python3-venv git
    # Audio (for Voice I/O in WSL2)
    portaudio19-dev libsndfile1 pulseaudio
    # Tor + proxychains
    tor proxychains-ng
    # General utilities
    curl wget net-tools
)

sudo apt-get install -y --no-install-recommends "${PACKAGES[@]}" 2>&1 | tail -5
success "System packages installed."

# ── 4. Clone / update repository ──────────────────────────────────────────────
if [[ -d "${INSTALL_DIR}/.git" ]]; then
    info "Repository already exists at ${INSTALL_DIR} – pulling latest…"
    git -C "${INSTALL_DIR}" pull --ff-only
else
    info "Cloning MirAI_OS to ${INSTALL_DIR}…"
    git clone "${REPO_URL}" "${INSTALL_DIR}"
fi
success "Repository ready."

# ── 5. Python virtual environment ─────────────────────────────────────────────
info "Setting up Python virtual environment…"
if [[ ! -d "${VENV_DIR}" ]]; then
    python3 -m venv "${VENV_DIR}"
fi
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip setuptools wheel -q
success "Virtual environment active."

# ── 6. Install Python dependencies ────────────────────────────────────────────
info "Installing Python packages (this may take a few minutes)…"
pip install -r "${INSTALL_DIR}/requirements.txt" -q
success "Python packages installed."

# ── 7. Configure .env ─────────────────────────────────────────────────────────
ENV_FILE="${INSTALL_DIR}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
    cp "${INSTALL_DIR}/.env.example" "${ENV_FILE}"
    warn ".env created from .env.example"
    warn "IMPORTANT: Edit ${ENV_FILE} and add your API keys before running MirAI."
    echo ""
    # Interactive prompts (skip if non-interactive / piped)
    if [[ -t 0 ]]; then
        read -rp "  Enter your OpenRouter API key (or press Enter to skip): " OR_KEY
        if [[ -n "${OR_KEY}" ]]; then
            # Use Python for safe substitution – avoids sed special-char injection
            python3 -c "
import sys, re
path = sys.argv[1]; key = sys.argv[2]
text = open(path).read()
text = re.sub(r'OPENROUTER_API_KEY=.*', 'OPENROUTER_API_KEY=' + key, text)
open(path, 'w').write(text)
" "${ENV_FILE}" "${OR_KEY}"
        fi
        read -rp "  Enter your Telegram bot token (or press Enter to skip): " TG_TOKEN
        if [[ -n "${TG_TOKEN}" ]]; then
            python3 -c "
import sys, re
path = sys.argv[1]; key = sys.argv[2]
text = open(path).read()
text = re.sub(r'TELEGRAM_BOT_TOKEN=.*', 'TELEGRAM_BOT_TOKEN=' + key, text)
open(path, 'w').write(text)
" "${ENV_FILE}" "${TG_TOKEN}"
        fi
        read -rp "  Enter your GitHub PAT (or press Enter to skip): " GH_TOKEN
        if [[ -n "${GH_TOKEN}" ]]; then
            python3 -c "
import sys, re
path = sys.argv[1]; key = sys.argv[2]
text = open(path).read()
text = re.sub(r'GITHUB_TOKEN=.*', 'GITHUB_TOKEN=' + key, text)
open(path, 'w').write(text)
" "${ENV_FILE}" "${GH_TOKEN}"
        fi
    fi
else
    info ".env already exists – skipping key prompts."
fi

# ── 8. Create data directory ───────────────────────────────────────────────────
mkdir -p "${DATA_DIR}"
success "Data directory ready: ${DATA_DIR}"

# ── 9. Configure Tor ──────────────────────────────────────────────────────────
info "Configuring Tor…"
# Enable ControlPort if not already set
if ! grep -q "^ControlPort 9051" /etc/tor/torrc 2>/dev/null; then
    echo "ControlPort 9051" | sudo tee -a /etc/tor/torrc > /dev/null
    echo "CookieAuthentication 1" | sudo tee -a /etc/tor/torrc > /dev/null
fi
# Start Tor (ignore errors – it may already be running or not available in WSL)
sudo service tor start 2>/dev/null || warn "Could not start Tor service (start it manually with: sudo service tor start)"
success "Tor configured."

# ── 10. Configure proxychains ──────────────────────────────────────────────────
PROXYCHAINS_CONF="/etc/proxychains4.conf"
if [[ -f "${PROXYCHAINS_CONF}" ]]; then
    # Ensure socks5 Tor entry is present
    if ! grep -q "socks5.*9050" "${PROXYCHAINS_CONF}"; then
        echo "socks5 127.0.0.1 9050" | sudo tee -a "${PROXYCHAINS_CONF}" > /dev/null
        success "proxychains configured with Tor SOCKS5."
    else
        info "proxychains already configured."
    fi
fi

# ── 11. WSL2 PulseAudio setup (optional) ──────────────────────────────────────
if grep -qi "microsoft" /proc/version 2>/dev/null; then
    info "WSL2 detected – configuring PulseAudio TCP forwarding for voice…"
    PULSE_CONF="${HOME}/.config/pulse/default.pa"
    mkdir -p "$(dirname "${PULSE_CONF}")"
    if [[ ! -f "${PULSE_CONF}" ]]; then
        cat > "${PULSE_CONF}" << 'PULSE_EOF'
.include /etc/pulse/default.pa
load-module module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1
PULSE_EOF
        success "PulseAudio TCP forwarding configured."
    fi
fi

# ── 12. Create convenience launcher ───────────────────────────────────────────
LAUNCHER="/usr/local/bin/mirai"
cat << LAUNCHER_EOF | sudo tee "${LAUNCHER}" > /dev/null
#!/usr/bin/env bash
source "${VENV_DIR}/bin/activate"
exec python "${INSTALL_DIR}/main.py" "\$@"
LAUNCHER_EOF
sudo chmod +x "${LAUNCHER}"
success "Launcher created: mirai (run 'mirai' or 'mirai telegram')"

# ── 13. Verify installation ────────────────────────────────────────────────────
info "Verifying installation…"
if python -c "import mirai; print('mirai package OK')" 2>/dev/null; then
    success "Import check passed."
else
    warn "Import check failed – check the requirements above for errors."
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}${GREEN}  MirAI_OS installation complete!  El Psy Congroo.     ${RESET}"
echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo -e "  1. Edit ${YELLOW}${ENV_FILE}${RESET} and fill in your API keys"
echo -e "  2. Start the CLI:      ${CYAN}mirai${RESET}"
echo -e "  3. Start Telegram bot: ${CYAN}mirai telegram${RESET}"
echo -e "  4. Self-mod preview:   ${CYAN}mirai selfmod 'add a new feature'${RESET}"
echo ""
