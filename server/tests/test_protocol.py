import struct
from protocol import (
    PacketType, parse_udp_packet, parse_tcp_packet,
    UDP_PORT, TCP_PORT,
)


class TestConstants:
    def test_udp_port(self):
        assert UDP_PORT == 19780

    def test_tcp_port(self):
        assert TCP_PORT == 19781


class TestParseUdpPacket:
    def test_mouse_move(self):
        dx, dy = 150, -200
        data = struct.pack("!bhh", 0x01, dx, dy)
        result = parse_udp_packet(data)
        assert result == (PacketType.MOUSE_MOVE, {"dx": 150, "dy": -200})

    def test_scroll(self):
        dy = -3
        data = struct.pack("!bh", 0x02, dy)
        result = parse_udp_packet(data)
        assert result == (PacketType.SCROLL, {"dy": -3})

    def test_unknown_udp_type_returns_none(self):
        data = struct.pack("!B", 0xFF)
        result = parse_udp_packet(data)
        assert result is None

    def test_truncated_mouse_packet_returns_none(self):
        data = struct.pack("!bh", 0x01, 10)  # missing dy
        result = parse_udp_packet(data)
        assert result is None


class TestParseTcpPacket:
    def test_left_click(self):
        data = struct.pack("!bb", 0x10, 2)  # action=click
        result = parse_tcp_packet(data)
        assert result == (PacketType.LEFT_CLICK, {"action": 2})

    def test_right_click(self):
        data = struct.pack("!bb", 0x11, 0)  # action=press
        result = parse_tcp_packet(data)
        assert result == (PacketType.RIGHT_CLICK, {"action": 0})

    def test_double_click(self):
        data = struct.pack("!b", 0x12)
        result = parse_tcp_packet(data)
        assert result == (PacketType.DOUBLE_CLICK, {})

    def test_key_press(self):
        data = struct.pack("!bHb", 0x20, 0x0041, 0)  # key=A, action=down
        result = parse_tcp_packet(data)
        assert result == (PacketType.KEY_PRESS, {"key_code": 0x0041, "action": 0})

    def test_key_text(self):
        text = "hello"
        encoded = text.encode("utf-8")
        data = struct.pack(f"!bH{len(encoded)}s", 0x21, len(encoded), encoded)
        result = parse_tcp_packet(data)
        assert result == (PacketType.KEY_TEXT, {"text": "hello"})

    def test_media_play_pause(self):
        data = struct.pack("!b", 0x30)
        result = parse_tcp_packet(data)
        assert result == (PacketType.MEDIA_PLAY_PAUSE, {})

    def test_media_next(self):
        data = struct.pack("!b", 0x31)
        result = parse_tcp_packet(data)
        assert result == (PacketType.MEDIA_NEXT, {})

    def test_media_prev(self):
        data = struct.pack("!b", 0x32)
        result = parse_tcp_packet(data)
        assert result == (PacketType.MEDIA_PREV, {})

    def test_volume_up(self):
        data = struct.pack("!b", 0x33)
        result = parse_tcp_packet(data)
        assert result == (PacketType.VOLUME_UP, {})

    def test_volume_down(self):
        data = struct.pack("!b", 0x34)
        result = parse_tcp_packet(data)
        assert result == (PacketType.VOLUME_DOWN, {})

    def test_volume_mute(self):
        data = struct.pack("!b", 0x35)
        result = parse_tcp_packet(data)
        assert result == (PacketType.VOLUME_MUTE, {})

    def test_unknown_tcp_type_returns_none(self):
        data = struct.pack("!B", 0xFF)
        result = parse_tcp_packet(data)
        assert result is None
