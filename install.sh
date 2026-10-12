#!/data/data/com.termux/files/usr/bin/bash
#
# media-compresser - Termux Installer
# Author: Musaddiq Shah.am
#

set -e

echo ""
echo "============================================"
echo "   media-compresser - Termux Installer"
echo "   by Musaddiq Shah.am"
echo "============================================"
echo ""

# Check Termux
if [ ! -d "/data/data/com.termux" ]; then
    echo "[!] Warning: This installer is designed for Termux."
    echo "    Continuing anyway..."
    echo ""
fi

# Update
echo "[1/3] Updating packages..."
pkg update -y >/dev/null 2>&1 || true

# Install
echo "[2/3] Installing Python and FFmpeg..."
pkg install python ffmpeg -y

# Done
echo "[3/3] Setup complete!"
echo ""
echo "============================================"
echo "   Installation Successful!"
echo "============================================"
echo ""
echo "To run:"
echo "   python media-compresser.py"
echo ""
echo "Optional: set up storage access"
echo "   termux-setup-storage"
echo ""
