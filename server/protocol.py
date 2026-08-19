import struct
from enum import IntEnum

UDP_PORT = 19780
TCP_PORT = 19781

MDNS_SERVICE_TYPE = "_openmouse._tcp.local."


class PacketType(IntEnum):
    MOUSE_MOVE = 0x01
    SCROLL = 0x02
    LEFT_CLICK = 0x10
    RIGHT_CLICK = 0x11
    DOUBLE_CLICK = 0x12
    KEY_PRESS = 0x20
    KEY_TEXT = 0x21
    MEDIA_PLAY_PAUSE = 0x30
    MEDIA_NEXT = 0x31
    MEDIA_PREV = 0x32
    VOLUME_UP = 0x33
    VOLUME_DOWN = 0x34
    VOLUME_MUTE = 0x35


# Codigos de tecla especiales.
#
# KEY_PRESS.key_code es un u16 que normalmente lleva un code point Unicode. Las
# teclas sin representacion textual (Enter, flechas, Shift, F1...) se envian en
# el Area de Uso Privado, que nunca aparece en texto real, asi que el rango es
# libre sin cambiar el formato del cable. Este mapa lo espeja
# app/lib/models/packet.dart — cambia ambos a la vez.
SPECIAL_KEY_BASE = 0xE000

SPECIAL_KEYS = {
    "enter": 0xE000,
    "backspace": 0xE001,
    "tab": 0xE002,
    "escape": 0xE003,
    "delete": 0xE004,
    "insert": 0xE005,
    "home": 0xE006,
    "end": 0xE007,
    "page_up": 0xE008,
    "page_down": 0xE009,
    "up": 0xE00A,
    "down": 0xE00B,
    "left": 0xE00C,
    "right": 0xE00D,
    "shift": 0xE00E,
    "shift_r": 0xE00F,
    "ctrl": 0xE010,
    "ctrl_r": 0xE011,
    "alt": 0xE012,
    "alt_r": 0xE013,
    "cmd": 0xE014,
    "cmd_r": 0xE015,
    "caps_lock": 0xE016,
    "f1": 0xE020,
    "f2": 0xE021,
    "f3": 0xE022,
    "f4": 0xE023,
    "f5": 0xE024,
    "f6": 0xE025,
    "f7": 0xE026,
    "f8": 0xE027,
    "f9": 0xE028,
    "f10": 0xE029,
    "f11": 0xE02A,
    "f12": 0xE02B,
}

SPECIAL_KEY_NAMES = {code: name for name, code in SPECIAL_KEYS.items()}


def parse_udp_packet(data: bytes) -> tuple[PacketType, dict] | None:
    """Parse a UDP packet. Returns (PacketType, payload_dict) or None."""
    if len(data) < 1:
        return None
    ptype = data[0]
    try:
        if ptype == PacketType.MOUSE_MOVE:
            if len(data) < 5:
                return None
            _, dx, dy = struct.unpack("!bhh", data[:5])
            return (PacketType.MOUSE_MOVE, {"dx": dx, "dy": dy})
        elif ptype == PacketType.SCROLL:
            if len(data) < 3:
                return None
            _, dy = struct.unpack("!bh", data[:3])
            return (PacketType.SCROLL, {"dy": dy})
    except struct.error:
        return None
    return None


def parse_tcp_packet(data: bytes) -> tuple[PacketType, dict] | None:
    """Parse a TCP packet. Returns (PacketType, payload_dict) or None."""
    if len(data) < 1:
        return None
    ptype = data[0]
    try:
        if ptype in (PacketType.LEFT_CLICK, PacketType.RIGHT_CLICK):
            if len(data) < 2:
                return None
            action = data[1]
            return (PacketType(ptype), {"action": action})
        elif ptype == PacketType.DOUBLE_CLICK:
            return (PacketType.DOUBLE_CLICK, {})
        elif ptype == PacketType.KEY_PRESS:
            if len(data) < 4:
                return None
            _, key_code, action = struct.unpack("!bHb", data[:4])
            return (PacketType.KEY_PRESS, {"key_code": key_code, "action": action})
        elif ptype == PacketType.KEY_TEXT:
            if len(data) < 3:
                return None
            _, length = struct.unpack("!bH", data[:3])
            if len(data) < 3 + length:
                return None
            text = data[3:3 + length].decode("utf-8")
            return (PacketType.KEY_TEXT, {"text": text})
        elif ptype in (
            PacketType.MEDIA_PLAY_PAUSE, PacketType.MEDIA_NEXT,
            PacketType.MEDIA_PREV, PacketType.VOLUME_UP,
            PacketType.VOLUME_DOWN, PacketType.VOLUME_MUTE,
        ):
            return (PacketType(ptype), {})
    except (struct.error, UnicodeDecodeError):
        return None
    return None
