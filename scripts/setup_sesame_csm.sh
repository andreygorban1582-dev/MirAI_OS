#!/bin/bash
# ============================================================
#  MirAI OS — Sesame CSM Voice Model Setup
#  Downloads and configures Character AI's open-source
#  Conversational Speech Model for Okabe's voice.
#  Run from inside the MirAI_OS directory.
#  El Psy Kongroo.
# ============================================================
set -euo pipefail

MODELS_DIR="./data/models"
CSM_DIR="$MODELS_DIR/csm"

echo "[FUTURE GADGET LAB] Setting up Sesame CSM voice model..."
echo "[!] Requires ~4GB disk space for model weights."

mkdir -p "$CSM_DIR"

# Clone Sesame CSM repo
if [ ! -d "$CSM_DIR/.git" ]; then
    echo "[⚡] Cloning Sesame CSM..."
    git clone https://github.com/SesameAILabs/csm.git "$CSM_DIR"
else
    echo "[✓] Sesame CSM already cloned. Pulling latest..."
    git -C "$CSM_DIR" pull
fi

# Install CSM dependencies
cd "$CSM_DIR"
pip install -r requirements.txt -q 2>/dev/null || true

# Download model weights from HuggingFace
echo "[⚡] Downloading CSM-1B model weights from HuggingFace..."
python3 - << 'PYEOF'
from huggingface_hub import hf_hub_download
import os

model_dir = os.path.dirname(os.path.abspath(__file__))
print(f"Downloading to: {model_dir}")

# Download CSM-1B weights
try:
    path = hf_hub_download(
        repo_id="sesame/csm-1b",
        filename="ckpt.pt",
        local_dir=model_dir,
    )
    print(f"[✓] Model downloaded: {path}")
except Exception as e:
    print(f"[!] Download failed: {e}")
    print("[!] You can manually download from: https://huggingface.co/sesame/csm-1b")
PYEOF

cd - > /dev/null

echo ""
echo "[✓] Sesame CSM setup complete!"
echo "[✓] Voice model path: $CSM_DIR"
echo ""
echo "MirAI will now speak with Hououin Kyouma's voice. El Psy Kongroo."
