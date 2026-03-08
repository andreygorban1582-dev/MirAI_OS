#!/usr/bin/env bash
# ─── MirAI_OS  –  Start (Linux / WSL2) ───────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

echo "[MirAI] Starting stack…"
docker compose up -d

echo
echo "  Agentverse :  https://localhost"
echo "  API        :  http://localhost:8080"
echo "  N8n        :  http://localhost:5678"
echo "  Kali noVNC :  http://localhost:6901"
echo
echo "[MirAI] Run 'docker compose logs -f' to follow logs."
