#!/usr/bin/env sh
# OpenMouse Linux installer.
# Usage: curl -fsSL https://raw.githubusercontent.com/Avzolem/OpenMouse/master/scripts/install.sh | sh
set -eu

REPO="Avzolem/OpenMouse"
INSTALL_DIR="$HOME/.local/share/openmouse"
BIN_PATH="$INSTALL_DIR/openmouse"
AUTOSTART="$HOME/.config/autostart/openmouse.desktop"

# 1. Detect architecture
case "$(uname -m)" in
    x86_64)
        ARCH="x86_64"
        ;;
    aarch64|arm64)
        ARCH="aarch64"
        ;;
    *)
        echo "OpenMouse: unsupported architecture: $(uname -m)" >&2
        echo "Supported: x86_64, aarch64" >&2
        exit 1
        ;;
esac

ASSET="openmouse-linux-${ARCH}"
echo "OpenMouse: detected ${ARCH}, looking for ${ASSET}..."

# 2. Resolve download URL from the latest release
URL=$(
    curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" \
        | grep "browser_download_url.*${ASSET}\"" \
        | head -n 1 \
        | cut -d '"' -f 4
)

if [ -z "$URL" ]; then
    echo "OpenMouse: no release asset found for ${ARCH}." >&2
    echo "Check https://github.com/${REPO}/releases" >&2
    exit 1
fi

# 3. Stop any running instance (we are about to overwrite the binary)
pkill -x openmouse 2>/dev/null || true

# 4. Download
mkdir -p "$INSTALL_DIR"
echo "OpenMouse: downloading from $URL"
curl -fsSL -o "$BIN_PATH" "$URL"
chmod +x "$BIN_PATH"

# 5. Autostart entry
mkdir -p "$(dirname "$AUTOSTART")"
cat > "$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=OpenMouse
Exec=$BIN_PATH
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF

# 6. Launch
nohup "$BIN_PATH" >/dev/null 2>&1 &

echo ""
echo "OpenMouse installed and running."
echo "Look for the green icon in your system tray — it shows your PC's IP."
echo "To uninstall: curl -fsSL https://raw.githubusercontent.com/${REPO}/master/scripts/uninstall.sh | sh"
