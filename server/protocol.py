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
