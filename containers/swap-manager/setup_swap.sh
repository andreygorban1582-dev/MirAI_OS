#!/bin/bash
# ─── MirAI Swap Manager  –  256 GB SSD→RAM swap ──────────────────────────────
# Runs as privileged container; writes swapfile to /swapspace mount.

set -e

SWAP_SIZE_GB="${SWAP_SIZE_GB:-256}"
SWAP_FILE="${SWAP_PATH:-/swapspace/mirai.swap}"
SWAP_BYTES=$(( SWAP_SIZE_GB * 1024 * 1024 * 1024 ))

echo "[swap] Target: ${SWAP_SIZE_GB} GB at ${SWAP_FILE}"

# Ensure mount point exists
mkdir -p "$(dirname "${SWAP_FILE}")"

# Remove stale swap file if it differs in size
if [ -f "${SWAP_FILE}" ]; then
    CURRENT_SIZE=$(stat -c%s "${SWAP_FILE}" 2>/dev/null || echo 0)
    if [ "${CURRENT_SIZE}" != "${SWAP_BYTES}" ]; then
        echo "[swap] Removing old swap file (${CURRENT_SIZE} bytes)"
        swapoff "${SWAP_FILE}" 2>/dev/null || true
        rm -f "${SWAP_FILE}"
    fi
fi

# Create swap file if not present
if [ ! -f "${SWAP_FILE}" ]; then
    echo "[swap] Creating ${SWAP_SIZE_GB} GB swap file…"
    dd if=/dev/zero of="${SWAP_FILE}" bs=1G count="${SWAP_SIZE_GB}" status=progress
    chmod 600 "${SWAP_FILE}"
    mkswap "${SWAP_FILE}"
fi

# Activate swap
if ! swapon --show | grep -q "${SWAP_FILE}"; then
    swapon "${SWAP_FILE}"
    echo "[swap] Activated ${SWAP_FILE}"
fi

# Tune kernel swap behaviour
# vm.swappiness=10  –  prefer RAM, use swap only when needed
# vm.vfs_cache_pressure=50  –  keep more dentries/inodes in RAM
sysctl -w vm.swappiness=10         2>/dev/null || true
sysctl -w vm.vfs_cache_pressure=50 2>/dev/null || true

echo "[swap] Current swap:"
swapon --show

echo "[swap] Memory overview:"
free -h

# Monitor loop: log swap usage every 5 min
while true; do
    sleep 300
    FREE=$(free -h | awk '/^Swap:/ {print "used=" $3 " free=" $4}')
    echo "[swap] ${FREE}"
done
