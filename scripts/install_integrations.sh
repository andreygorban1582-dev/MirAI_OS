#!/bin/bash
# ============================================================
#  MirAI OS — Optional Integration Installer
#  Run inside WSL2 Kali with venv activated.
#  Usage: bash scripts/install_integrations.sh [OPTIONS]
#
#  Options:
#    --all         Install everything
#    --groq        Groq (fastest free LLM)
#    --together    Together.ai (large models)
#    --tavily      Tavily search
#    --mem0        Mem0 cloud memory
#    --qdrant      Qdrant vector store
#    --ngrok       Ngrok tunnel
#    --voice       Sesame CSM voice
#  El Psy Kongroo.
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${CYAN}[FUTURE GADGET LAB]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }

install_groq() {
    log "Installing Groq (fastest free LLM)..."
    pip install groq -q
    ok "Groq installed. Add GROQ_API_KEY to .env"
    ok "Get free key: https://console.groq.com"
    echo "  Then set: integrations.groq.enabled: true in settings.yaml"
}

install_together() {
    log "Installing Together.ai..."
    pip install together -q
    ok "Together.ai installed. Add TOGETHER_API_KEY to .env"
    ok "Get key + free credit: https://api.together.xyz"
}

install_tavily() {
    log "Installing Tavily search..."
    pip install tavily-python -q
    ok "Tavily installed. Add TAVILY_API_KEY to .env"
    ok "Get free 1000/month key: https://tavily.com"
}

install_mem0() {
    log "Installing Mem0 cloud memory..."
    pip install mem0ai -q
    ok "Mem0 installed. Add MEM0_API_KEY to .env"
    ok "Signup: https://mem0.ai"
}

install_qdrant() {
    log "Installing Qdrant cloud vector store..."
    pip install qdrant-client -q
    ok "Qdrant installed. Add QDRANT_URL + QDRANT_API_KEY to .env"
    ok "Free 1GB: https://cloud.qdrant.io"
}

install_ngrok() {
    log "Installing Ngrok tunnel..."
    pip install ngrok -q
    ok "Ngrok installed. Add NGROK_AUTH_TOKEN to .env"
    ok "Free signup: https://ngrok.com"
}

install_cloudflare() {
    log "Installing cloudflared binary..."
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
        -o /usr/local/bin/cloudflared
    chmod +x /usr/local/bin/cloudflared
    ok "cloudflared installed."
    warn "For named tunnel: CLOUDFLARE_TUNNEL_TOKEN in .env"
    warn "For quick tunnel: set integrations.cloudflare_tunnel.quick_tunnel: true in settings.yaml"
    ok "Docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps"
}

install_voice() {
    log "Installing Sesame CSM voice model..."
    bash "$(dirname "$0")/setup_sesame_csm.sh"
}

# ── Parse args ────────────────────────────────────────────────
if [ $# -eq 0 ]; then
    echo "Usage: $0 [--all] [--groq] [--together] [--tavily] [--mem0] [--qdrant] [--ngrok] [--cloudflare] [--voice]"
    exit 0
fi

for arg in "$@"; do
    case $arg in
        --all)
            install_groq
            install_together
            install_tavily
            install_mem0
            install_qdrant
            install_ngrok
            install_cloudflare
            ;;
        --groq)        install_groq ;;
        --together)    install_together ;;
        --tavily)      install_tavily ;;
        --mem0)        install_mem0 ;;
        --qdrant)      install_qdrant ;;
        --ngrok)       install_ngrok ;;
        --cloudflare)  install_cloudflare ;;
        --voice)       install_voice ;;
        *) warn "Unknown option: $arg" ;;
    esac
done

echo ""
ok "Integration installation complete!"
warn "Remember to edit .env with your API keys, then restart MirAI."
echo "El Psy Kongroo."
