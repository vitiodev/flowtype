#!/bin/bash
set -e

echo "=== FlowType installer for Ubuntu 24 ==="

# System dependencies
echo "[1/4] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3-pip python3-venv \
    ydotool wl-clipboard \
    portaudio19-dev ffmpeg

# input group for evdev
if ! groups | grep -q '\binput\b'; then
    echo "[2/4] Adding $USER to 'input' group..."
    sudo usermod -aG input "$USER"
    echo "      ⚠  Re-login required for group change to take effect."
else
    echo "[2/4] User already in 'input' group."
fi

# ydotoold service (needed for ydotool to work on Wayland)
echo "[3/4] Enabling ydotoold service..."
sudo systemctl enable --now ydotoold 2>/dev/null \
    || echo "      Note: ydotoold service not found. Start manually: sudo ydotoold &"

# Python venv + deps
echo "[4/4] Creating venv and installing Python packages..."
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "=== Done! ==="
echo ""
echo "Run with:"
echo "  source venv/bin/activate && python flowtype.py"
echo ""
echo "Hold RIGHT SHIFT to record voice, release to transcribe and type."
echo ""
echo "Config: ~/.config/flowtype/config.json"
echo "  model: tiny | base | small | medium | large  (default: base)"
echo "  language: 'ru' | 'en' | null (auto)"
echo "  device: 'cpu' | 'cuda'"
