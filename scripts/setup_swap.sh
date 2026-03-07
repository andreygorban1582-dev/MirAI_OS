#!/bin/bash
# ============================================================
#  MirAI OS — 128GB Swap Setup for WSL2 Legion Go
#  Gives Kali Linux virtually unlimited working memory.
#  Run this INSIDE WSL2 as root.
#  El Psy Kongroo.
# ============================================================
set -euo pipefail

SWAP_SIZE_GB=${1:-128}
SWAP_FILE="/swap_mirai_${SWAP_SIZE_GB}gb.img"

echo "[FUTURE GADGET LAB] Creating ${SWAP_SIZE_GB}GB swap file at ${SWAP_FILE}..."
echo "[!] This may take a few minutes on the Legion Go's SSD."
echo ""

# Disable existing swap
sudo swapoff -a 2>/dev/null || true

# Create the swap file using dd (faster than fallocate on WSL)
echo "[⚡] Allocating ${SWAP_SIZE_GB}GB..."
sudo dd if=/dev/zero of="$SWAP_FILE" bs=1G count=$SWAP_SIZE_GB status=progress

# Secure and format
sudo chmod 600 "$SWAP_FILE"
sudo mkswap "$SWAP_FILE"

# Enable it
sudo swapon "$SWAP_FILE"

# Add to /etc/fstab for persistence
if ! grep -q "$SWAP_FILE" /etc/fstab; then
    echo "$SWAP_FILE none swap sw 0 0" | sudo tee -a /etc/fstab
fi

# Configure swappiness (low = use RAM more, only swap when needed)
echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Show result
echo ""
echo "[✓] Swap configured:"
free -h
echo ""
echo "[✓] swapon -s:"
swapon -s
echo ""
echo "[FUTURE GADGET LAB] 128GB of quantum memory space secured!"
echo "The Organization's memory limits no longer apply. El Psy Kongroo."
