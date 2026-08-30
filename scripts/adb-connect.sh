#!/bin/sh
# Reconecta por ADB inalambrico al movil de pruebas sin volver a emparejar.
#
# Orden de intentos:
#   1. Endpoint guardado del ultimo exito.
#   2. Descubrimiento mDNS (_adb-tls-connect._tcp), primero con el adb de WSL
#      y luego con el adb.exe de Windows, que si recibe multicast de la LAN.
#   3. Se rinde y pide el puerto. Nunca escanea puertos del movil.
#
# Uso:
#   ./adb-connect.sh                  reconecta solo
#   ./adb-connect.sh 44671            fuerza puerto, reutiliza la IP guardada
#   ./adb-connect.sh 192.168.1.80:44671   fuerza IP y puerto
set -eu

STATE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/openmouse"
STATE_FILE="$STATE_DIR/adb-endpoint"

# adb.exe de Windows: unico camino con acceso al multicast de la LAN mientras
# WSL siga en modo NAT. Si no aparece, el descubrimiento simplemente se salta.
# Se puede fijar a mano con OPENMOUSE_WIN_ADB.
WIN_ADB="${OPENMOUSE_WIN_ADB:-}"
if [ -z "$WIN_ADB" ]; then
    WIN_ADB=$(command -v adb.exe 2>/dev/null || true)
fi
if [ -z "$WIN_ADB" ]; then
    WIN_ADB=$(ls -1 /mnt/c/Users/*/AppData/Local/Microsoft/WinGet/Packages/Genymobile.scrcpy_*/scrcpy-win64-*/adb.exe 2>/dev/null | head -1)
fi

export ADB_MDNS_OPENSCREEN=1

log() { printf '%s\n' "$*" >&2; }

save_endpoint() {
    mkdir -p "$STATE_DIR"
    printf '%s\n' "$1" > "$STATE_FILE"
}

load_endpoint() {
    [ -f "$STATE_FILE" ] || return 1
    read -r saved < "$STATE_FILE" || return 1
    [ -n "$saved" ] || return 1
    printf '%s\n' "$saved"
}

# adb connect devuelve 0 aunque falle, asi que hay que mirar la salida. Y un
# dispositivo puede aparecer como "offline", que tampoco sirve para nada.
try_connect() {
    endpoint="$1"
    log "-> probando $endpoint"
    out=$(timeout 20 adb connect "$endpoint" 2>&1 || true)
    case "$out" in
        *"connected to"*) ;;
        *)
            reason=$(printf '%s' "$out" | head -1)
            log "   ${reason:-sin respuesta, tiempo agotado}"
            return 1
            ;;
    esac
    state=$(adb devices 2>/dev/null | awk -v e="$endpoint" '$1 == e { print $2 }')
    if [ "$state" != "device" ]; then
        log "   conectado pero en estado '${state:-desconocido}'"
        adb disconnect "$endpoint" >/dev/null 2>&1 || true
        return 1
    fi
    return 0
}

# Extrae "IP:puerto" de la tabla de `adb mdns services`, que tiene la forma:
#   adb-SERIAL-xxxxxx  _adb-tls-connect._tcp  192.168.1.80:44671
discover_with() {
    timeout 25 "$1" mdns services 2>/dev/null \
        | awk '$2 == "_adb-tls-connect._tcp" { print $3 }' \
        | head -1
}

discover() {
    log "-> buscando por mDNS con el adb de WSL"
    found=$(discover_with adb || true)
    if [ -n "$found" ]; then
        printf '%s\n' "$found"
        return 0
    fi
    [ -x "$WIN_ADB" ] || return 1
    log "-> buscando por mDNS con el adb.exe de Windows"
    found=$(discover_with "$WIN_ADB" || true)
    [ -n "$found" ] || return 1
    printf '%s\n' "$found"
}

saved=$(load_endpoint || true)

# Un argumento suelto puede ser el puerto a secas o el endpoint completo.
target=""
if [ $# -gt 0 ]; then
    case "$1" in
        *:*) target="$1" ;;
        *)
            [ -n "$saved" ] || { log "no hay IP guardada: pasa 'IP:puerto' entero"; exit 2; }
            target="${saved%%:*}:$1"
            ;;
    esac
elif [ -n "$saved" ]; then
    target="$saved"
fi

if [ -n "$target" ] && try_connect "$target"; then
    save_endpoint "$target"
    log "conectado a $target"
    exit 0
fi

if found=$(discover) && [ -n "$found" ] && try_connect "$found"; then
    save_endpoint "$found"
    log "conectado a $found (descubierto por mDNS)"
    exit 0
fi

log ""
log "no se pudo conectar."
log "Comprueba que el movil este en la WiFi y con la depuracion inalambrica activa."
log "Si sigue fallando, mira el puerto en Ajustes > Opciones de desarrollador >"
log "Depuracion inalambrica y ejecuta:  $0 <puerto>"
exit 1
