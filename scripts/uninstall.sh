#!/usr/bin/env sh
# OpenMouse Linux uninstaller.
# Usage: curl -fsSL https://raw.githubusercontent.com/Avzolem/OpenMouse/master/scripts/uninstall.sh | sh
set -eu

INSTALL_DIR="$HOME/.local/share/openmouse"
AUTOSTART="$HOME/.config/autostart/openmouse.desktop"

pkill -x openmouse 2>/dev/null || true
rm -rf "$INSTALL_DIR"
rm -f "$AUTOSTART"

echo "OpenMouse removed."
