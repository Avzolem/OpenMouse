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
# Bajamos a un temporal y movemos al final: escribir directamente sobre
# $BIN_PATH deja un binario truncado pero ejecutable si la descarga se corta,
# y el autostart apuntaria a el.
mkdir -p "$INSTALL_DIR"
TMP_PATH="$BIN_PATH.download"
trap 'rm -f "$TMP_PATH"' EXIT INT TERM
echo "OpenMouse: downloading from $URL"
curl -fsSL -o "$TMP_PATH" "$URL"

if [ ! -s "$TMP_PATH" ]; then
    echo "OpenMouse: download failed (empty file)." >&2
    exit 1
fi

chmod +x "$TMP_PATH"
mv -f "$TMP_PATH" "$BIN_PATH"
trap - EXIT INT TERM

# 5. Autostart entry
mkdir -p "$(dirname "$AUTOSTART")"
cat > "$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=OpenMouse
Comment=Control your PC from your phone over WiFi
Exec=$BIN_PATH
Terminal=false
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
