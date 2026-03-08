#!/usr/bin/env bash
# ============================================================
# MirAI_OS – Build installer executable (Linux/macOS)
# Requires: Python 3.9+ and pip
# Usage: bash build_exe.sh
# ============================================================

set -euo pipefail

echo ""
echo "============================================================"
echo " MirAI_OS Installer Builder"
echo "============================================================"
echo ""

# Detect Python
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)
if [ -z "$PYTHON" ]; then
    echo "[ERROR] Python 3 not found. Install Python 3.9+ first."
    exit 1
fi
echo "[OK] Python: $PYTHON ($($PYTHON --version 2>&1))"

# Install PyInstaller
echo "[INFO] Installing/upgrading PyInstaller..."
"$PYTHON" -m pip install --quiet --upgrade pyinstaller

# Install runtime deps
echo "[INFO] Installing runtime dependencies..."
"$PYTHON" -m pip install --quiet -r requirements.txt

# Clean previous build
echo "[INFO] Cleaning previous build artifacts..."
rm -rf build dist

# Run PyInstaller
echo "[INFO] Building MirAI_OS_Installer..."
"$PYTHON" -m PyInstaller --clean --noconfirm mirai_installer.spec

echo ""
echo "============================================================"
echo " Build complete!"
echo " Installer: dist/MirAI_OS_Installer"
echo "============================================================"
echo ""
