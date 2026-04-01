# OpenMouse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a remote mouse/keyboard/media controller — Android Flutter app + Python desktop server communicating over WiFi.

**Architecture:** UDP for high-frequency mouse/scroll data, TCP for reliable keyboard/click/media commands. mDNS for auto-discovery. Server uses pynput for input simulation, pystray for system tray. Flutter app uses dart:io for networking, bonsoir for mDNS, GestureDetector for touch input.

**Tech Stack:** Python 3.11+ (asyncio, pynput, pystray, zeroconf, Pillow), Flutter (dart:io, bonsoir)

---

## File Structure

### Server (`server/`)

| File | Responsibility |
|------|---------------|
| `server/openmouse.py` | Entry point — starts all components |
| `server/protocol.py` | Packet type constants + parsing/encoding |
| `server/input_handler.py` | Translates parsed packets → pynput actions |
| `server/network.py` | UDP + TCP asyncio listeners |
| `server/discovery.py` | mDNS service registration via zeroconf |
| `server/tray.py` | System tray icon + menu via pystray |
| `server/requirements.txt` | Dependencies |
| `server/tests/test_protocol.py` | Protocol parsing tests |
| `server/tests/test_input_handler.py` | Input handler tests (mocked pynput) |
| `server/tests/test_network.py` | Network listener tests |

### Flutter App (`app/`)

| File | Responsibility |
|------|---------------|
| `app/lib/main.dart` | App entry point + MaterialApp |
| `app/lib/models/packet.dart` | Binary packet encoding per protocol |
| `app/lib/services/connection_service.dart` | Manages UDP + TCP sockets to server |
| `app/lib/services/discovery_service.dart` | mDNS discovery via bonsoir |
| `app/lib/screens/home_screen.dart` | Server list + manual IP + connect |
| `app/lib/screens/control_screen.dart` | Main screen with bottom nav (trackpad/keyboard/media) |
| `app/lib/widgets/trackpad.dart` | Touch zone + scroll bar |
| `app/lib/widgets/keyboard_input.dart` | Keyboard capture + text input |
| `app/lib/widgets/media_controls.dart` | Media + volume buttons |
| `app/test/models/packet_test.dart` | Packet encoding tests |
| `app/test/services/connection_service_test.dart` | Connection service tests |

---

## Task 1: Server — Protocol Module

**Files:**
- Create: `server/protocol.py`
- Create: `server/tests/__init__.py`
- Create: `server/tests/test_protocol.py`

- [ ] **Step 1: Write failing tests for protocol parsing**

```python
# server/tests/test_protocol.py
import struct
import pytest
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
        data = struct.pack("!b", 0xFF)
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
        data = struct.pack("!b", 0xFF)
        result = parse_tcp_packet(data)
        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_protocol.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'protocol'`

- [ ] **Step 3: Implement protocol module**

```python
# server/protocol.py
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


def parse_udp_packet(data: bytes):
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


def parse_tcp_packet(data: bytes):
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
```

Also create empty `server/tests/__init__.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_protocol.py -v`
Expected: All 16 tests PASS

- [ ] **Step 5: Commit**

```bash
git add server/protocol.py server/tests/__init__.py server/tests/test_protocol.py
git commit -m "feat(server): add protocol module with packet parsing"
```

---

## Task 2: Server — Input Handler

**Files:**
- Create: `server/input_handler.py`
- Create: `server/tests/test_input_handler.py`

- [ ] **Step 1: Write failing tests for input handler**

```python
# server/tests/test_input_handler.py
from unittest.mock import MagicMock, patch, call
import pytest
from input_handler import InputHandler


@pytest.fixture
def handler():
    with patch("input_handler.mouse_controller") as mock_mouse, \
         patch("input_handler.keyboard_controller") as mock_kb:
        h = InputHandler()
        h._mouse = mock_mouse
        h._keyboard = mock_kb
        yield h


class TestMouseMove:
    def test_move(self, handler):
        handler.move(10, -5)
        handler._mouse.move.assert_called_once_with(10, -5)


class TestScroll:
    def test_scroll_up(self, handler):
        handler.scroll(-3)
        handler._mouse.scroll.assert_called_once_with(0, -3)

    def test_scroll_down(self, handler):
        handler.scroll(5)
        handler._mouse.scroll.assert_called_once_with(0, 5)


class TestClick:
    def test_left_click(self, handler):
        with patch("input_handler.Button") as MockButton:
            handler.click("left", 2)
            handler._mouse.click.assert_called_once_with(MockButton.left, 1)

    def test_left_press(self, handler):
        with patch("input_handler.Button") as MockButton:
            handler.click("left", 0)
            handler._mouse.press.assert_called_once_with(MockButton.left)

    def test_left_release(self, handler):
        with patch("input_handler.Button") as MockButton:
            handler.click("left", 1)
            handler._mouse.release.assert_called_once_with(MockButton.left)

    def test_right_click(self, handler):
        with patch("input_handler.Button") as MockButton:
            handler.click("right", 2)
            handler._mouse.click.assert_called_once_with(MockButton.right, 1)

    def test_double_click(self, handler):
        with patch("input_handler.Button") as MockButton:
            handler.double_click()
            handler._mouse.click.assert_called_once_with(MockButton.left, 2)


class TestMedia:
    def test_play_pause(self, handler):
        with patch("input_handler.Key") as MockKey:
            handler.media("play_pause")
            handler._keyboard.press.assert_called_once_with(MockKey.media_play_pause)
            handler._keyboard.release.assert_called_once_with(MockKey.media_play_pause)

    def test_volume_up(self, handler):
        with patch("input_handler.Key") as MockKey:
            handler.media("volume_up")
            handler._keyboard.press.assert_called_once_with(MockKey.media_volume_up)
            handler._keyboard.release.assert_called_once_with(MockKey.media_volume_up)


class TestKeyText:
    def test_type_text(self, handler):
        handler.type_text("hello")
        handler._keyboard.type.assert_called_once_with("hello")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_input_handler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'input_handler'`

- [ ] **Step 3: Implement input handler**

```python
# server/input_handler.py
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

mouse_controller = MouseController()
keyboard_controller = KeyboardController()


class InputHandler:
    def __init__(self):
        self._mouse = mouse_controller
        self._keyboard = keyboard_controller

    def move(self, dx: int, dy: int):
        self._mouse.move(dx, dy)

    def scroll(self, dy: int):
        self._mouse.scroll(0, dy)

    def click(self, button: str, action: int):
        btn = Button.left if button == "left" else Button.right
        if action == 0:
            self._mouse.press(btn)
        elif action == 1:
            self._mouse.release(btn)
        elif action == 2:
            self._mouse.click(btn, 1)

    def double_click(self):
        self._mouse.click(Button.left, 2)

    def key_press(self, key_code: int, action: int):
        try:
            key = KeyboardController()  # unused, we use chr
            char = chr(key_code)
        except (ValueError, OverflowError):
            return
        if action == 0:
            self._keyboard.press(char)
        elif action == 1:
            self._keyboard.release(char)

    def type_text(self, text: str):
        self._keyboard.type(text)

    def media(self, command: str):
        media_keys = {
            "play_pause": Key.media_play_pause,
            "next": Key.media_next,
            "prev": Key.media_previous,
            "volume_up": Key.media_volume_up,
            "volume_down": Key.media_volume_down,
            "volume_mute": Key.media_volume_mute,
        }
        key = media_keys.get(command)
        if key:
            self._keyboard.press(key)
            self._keyboard.release(key)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_input_handler.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add server/input_handler.py server/tests/test_input_handler.py
git commit -m "feat(server): add input handler with pynput integration"
```

---

## Task 3: Server — Network Listeners (UDP + TCP)

**Files:**
- Create: `server/network.py`
- Create: `server/tests/test_network.py`

- [ ] **Step 1: Write failing tests for network module**

```python
# server/tests/test_network.py
import asyncio
import struct
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from protocol import PacketType, UDP_PORT, TCP_PORT


class TestUdpServer:
    @pytest.mark.asyncio
    async def test_receives_mouse_move_and_calls_handler(self):
        from network import UdpServer
        handler = MagicMock()
        server = UdpServer(handler, host="127.0.0.1", port=0)
        await server.start()
        port = server.port

        sock = await asyncio.to_thread(self._send_udp, port, struct.pack("!bhh", 0x01, 10, -20))
        await asyncio.sleep(0.05)

        handler.move.assert_called_with(10, -20)
        await server.stop()

    @pytest.mark.asyncio
    async def test_receives_scroll_and_calls_handler(self):
        from network import UdpServer
        handler = MagicMock()
        server = UdpServer(handler, host="127.0.0.1", port=0)
        await server.start()
        port = server.port

        await asyncio.to_thread(self._send_udp, port, struct.pack("!bh", 0x02, -5))
        await asyncio.sleep(0.05)

        handler.scroll.assert_called_with(-5)
        await server.stop()

    @staticmethod
    def _send_udp(port, data):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(data, ("127.0.0.1", port))
        s.close()


class TestTcpServer:
    @pytest.mark.asyncio
    async def test_receives_left_click_and_calls_handler(self):
        from network import TcpServer
        handler = MagicMock()
        server = TcpServer(handler, host="127.0.0.1", port=0)
        await server.start()
        port = server.port

        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        packet = struct.pack("!bb", 0x10, 2)
        length_prefix = struct.pack("!H", len(packet))
        writer.write(length_prefix + packet)
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        await asyncio.sleep(0.05)

        handler.click.assert_called_with("left", 2)
        await server.stop()

    @pytest.mark.asyncio
    async def test_receives_media_command(self):
        from network import TcpServer
        handler = MagicMock()
        server = TcpServer(handler, host="127.0.0.1", port=0)
        await server.start()
        port = server.port

        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        packet = struct.pack("!b", 0x30)
        length_prefix = struct.pack("!H", len(packet))
        writer.write(length_prefix + packet)
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        await asyncio.sleep(0.05)

        handler.media.assert_called_with("play_pause")
        await server.stop()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_network.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'network'`

- [ ] **Step 3: Implement network module**

```python
# server/network.py
import asyncio
import struct
import logging
from protocol import PacketType, parse_udp_packet, parse_tcp_packet

logger = logging.getLogger("openmouse.network")


class UdpServer:
    def __init__(self, handler, host="0.0.0.0", port=19780):
        self._handler = handler
        self._host = host
        self._port = port
        self._transport = None
        self._protocol = None

    @property
    def port(self):
        if self._transport:
            return self._transport.get_extra_info("sockname")[1]
        return self._port

    async def start(self):
        loop = asyncio.get_running_loop()
        self._transport, self._protocol = await loop.create_datagram_endpoint(
            lambda: _UdpProtocol(self._handler),
            local_addr=(self._host, self._port),
        )
        logger.info(f"UDP server listening on {self._host}:{self.port}")

    async def stop(self):
        if self._transport:
            self._transport.close()


class _UdpProtocol(asyncio.DatagramProtocol):
    def __init__(self, handler):
        self._handler = handler

    def datagram_received(self, data, addr):
        result = parse_udp_packet(data)
        if result is None:
            return
        ptype, payload = result
        if ptype == PacketType.MOUSE_MOVE:
            self._handler.move(payload["dx"], payload["dy"])
        elif ptype == PacketType.SCROLL:
            self._handler.scroll(payload["dy"])


class TcpServer:
    def __init__(self, handler, host="0.0.0.0", port=19781):
        self._handler = handler
        self._host = host
        self._port = port
        self._server = None
        self.on_client_connected = None
        self.on_client_disconnected = None

    @property
    def port(self):
        if self._server and self._server.sockets:
            return self._server.sockets[0].getsockname()[1]
        return self._port

    async def start(self):
        self._server = await asyncio.start_server(
            self._handle_client, self._host, self._port,
        )
        logger.info(f"TCP server listening on {self._host}:{self.port}")

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        logger.info(f"Client connected: {addr}")
        if self.on_client_connected:
            self.on_client_connected(addr)
        try:
            while True:
                length_data = await reader.readexactly(2)
                length = struct.unpack("!H", length_data)[0]
                data = await reader.readexactly(length)
                self._dispatch(data)
        except (asyncio.IncompleteReadError, ConnectionResetError):
            logger.info(f"Client disconnected: {addr}")
        finally:
            if self.on_client_disconnected:
                self.on_client_disconnected(addr)
            writer.close()

    def _dispatch(self, data: bytes):
        result = parse_tcp_packet(data)
        if result is None:
            return
        ptype, payload = result
        if ptype == PacketType.LEFT_CLICK:
            self._handler.click("left", payload["action"])
        elif ptype == PacketType.RIGHT_CLICK:
            self._handler.click("right", payload["action"])
        elif ptype == PacketType.DOUBLE_CLICK:
            self._handler.double_click()
        elif ptype == PacketType.KEY_PRESS:
            self._handler.key_press(payload["key_code"], payload["action"])
        elif ptype == PacketType.KEY_TEXT:
            self._handler.type_text(payload["text"])
        elif ptype == PacketType.MEDIA_PLAY_PAUSE:
            self._handler.media("play_pause")
        elif ptype == PacketType.MEDIA_NEXT:
            self._handler.media("next")
        elif ptype == PacketType.MEDIA_PREV:
            self._handler.media("prev")
        elif ptype == PacketType.VOLUME_UP:
            self._handler.media("volume_up")
        elif ptype == PacketType.VOLUME_DOWN:
            self._handler.media("volume_down")
        elif ptype == PacketType.VOLUME_MUTE:
            self._handler.media("volume_mute")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && pip install pytest-asyncio && python -m pytest tests/test_network.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add server/network.py server/tests/test_network.py
git commit -m "feat(server): add UDP and TCP network listeners"
```

---

## Task 4: Server — mDNS Discovery

**Files:**
- Create: `server/discovery.py`

- [ ] **Step 1: Implement discovery module**

```python
# server/discovery.py
import socket
import logging
from zeroconf import Zeroconf, ServiceInfo
from protocol import MDNS_SERVICE_TYPE, TCP_PORT, UDP_PORT

logger = logging.getLogger("openmouse.discovery")


class Discovery:
    def __init__(self, tcp_port: int = TCP_PORT, udp_port: int = UDP_PORT):
        self._zeroconf = None
        self._info = None
        self._tcp_port = tcp_port
        self._udp_port = udp_port

    def get_local_ip(self) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"
        finally:
            s.close()

    def start(self):
        ip = self.get_local_ip()
        hostname = socket.gethostname()
        self._zeroconf = Zeroconf()
        self._info = ServiceInfo(
            MDNS_SERVICE_TYPE,
            f"OpenMouse on {hostname}.{MDNS_SERVICE_TYPE}",
            addresses=[socket.inet_aton(ip)],
            port=self._tcp_port,
            properties={"udp_port": str(self._udp_port)},
        )
        self._zeroconf.register_service(self._info)
        logger.info(f"mDNS: published as 'OpenMouse on {hostname}' at {ip}")
        return ip

    def stop(self):
        if self._zeroconf and self._info:
            self._zeroconf.unregister_service(self._info)
            self._zeroconf.close()
            logger.info("mDNS: service unregistered")
```

- [ ] **Step 2: Manual test — run discovery and check with avahi-browse or dns-sd**

Run: `cd server && python -c "from discovery import Discovery; d = Discovery(); ip = d.start(); print(f'Published at {ip}'); input('Press Enter to stop'); d.stop()"`
Expected: Service appears, can be seen with `avahi-browse -r _openmouse._tcp` (Linux) or dns-sd (Windows)

- [ ] **Step 3: Commit**

```bash
git add server/discovery.py
git commit -m "feat(server): add mDNS service discovery"
```

---

## Task 5: Server — System Tray

**Files:**
- Create: `server/tray.py`
- Create: `server/icon.png`

- [ ] **Step 1: Generate a simple tray icon**

```python
# Run once to generate icon.png:
# cd server && python -c "
from PIL import Image, ImageDraw
img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.ellipse([8, 8, 56, 56], fill=(76, 175, 80))  # green circle
draw.ellipse([24, 20, 40, 36], fill=(255, 255, 255))  # white dot (mouse pointer)
img.save('icon.png')
# "
```

- [ ] **Step 2: Implement tray module**

```python
# server/tray.py
import threading
import logging
from pathlib import Path
from PIL import Image
import pystray

logger = logging.getLogger("openmouse.tray")


class Tray:
    def __init__(self, ip: str, on_quit):
        self._ip = ip
        self._on_quit = on_quit
        self._icon = None
        self._thread = None
        self._status = "Waiting for connection..."

    def set_status(self, status: str):
        self._status = status
        if self._icon:
            self._icon.update_menu()

    def start(self):
        icon_path = Path(__file__).parent / "icon.png"
        image = Image.open(icon_path)

        def make_menu():
            return pystray.Menu(
                pystray.MenuItem(f"IP: {self._ip}", None, enabled=False),
                pystray.MenuItem(self._status, None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._quit),
            )

        self._icon = pystray.Icon(
            "openmouse",
            image,
            "OpenMouse",
            menu=make_menu(),
        )
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()
        logger.info("System tray started")

    def _quit(self, icon, item):
        icon.stop()
        self._on_quit()

    def stop(self):
        if self._icon:
            self._icon.stop()
```

- [ ] **Step 3: Commit**

```bash
git add server/tray.py server/icon.png
git commit -m "feat(server): add system tray with pystray"
```

---

## Task 6: Server — Entry Point + Requirements

**Files:**
- Create: `server/openmouse.py`
- Create: `server/requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
pynput
pystray
Pillow
zeroconf
pytest
pytest-asyncio
```

- [ ] **Step 2: Implement entry point**

```python
# server/openmouse.py
import asyncio
import logging
import signal
import sys
from input_handler import InputHandler
from network import UdpServer, TcpServer
from discovery import Discovery
from tray import Tray
from protocol import UDP_PORT, TCP_PORT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("openmouse")


async def main():
    handler = InputHandler()
    udp_server = UdpServer(handler, port=UDP_PORT)
    tcp_server = TcpServer(handler, port=TCP_PORT)
    discovery = Discovery(tcp_port=TCP_PORT, udp_port=UDP_PORT)

    stop_event = asyncio.Event()

    def quit_app():
        stop_event.set()

    ip = discovery.start()
    logger.info(f"OpenMouse server running at {ip}")

    tray = Tray(ip, on_quit=quit_app)

    def on_connect(addr):
        tray.set_status(f"Connected: {addr[0]}")

    def on_disconnect(addr):
        tray.set_status("Waiting for connection...")

    tcp_server.on_client_connected = on_connect
    tcp_server.on_client_disconnected = on_disconnect

    await udp_server.start()
    await tcp_server.start()
    tray.start()

    logger.info(f"Listening — UDP:{UDP_PORT} TCP:{TCP_PORT}")

    await stop_event.wait()

    tray.stop()
    await udp_server.stop()
    await tcp_server.stop()
    discovery.stop()
    logger.info("OpenMouse stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
```

- [ ] **Step 3: Install dependencies and run**

Run: `cd server && pip install -r requirements.txt && python openmouse.py`
Expected: Server starts, tray icon appears, logs show listening on both ports

- [ ] **Step 4: Commit**

```bash
git add server/openmouse.py server/requirements.txt
git commit -m "feat(server): add entry point and requirements"
```

---

## Task 7: Flutter — Project Setup + Packet Model

**Files:**
- Create: Flutter project at `app/`
- Create: `app/lib/models/packet.dart`
- Create: `app/test/models/packet_test.dart`

- [ ] **Step 1: Create Flutter project**

Run: `cd /home/avsolem/sites/openmouse && flutter create --org com.openmouse --project-name openmouse app`

- [ ] **Step 2: Add bonsoir dependency**

Run: `cd app && flutter pub add bonsoir`

- [ ] **Step 3: Write failing test for packet encoding**

```dart
// app/test/models/packet_test.dart
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:openmouse/models/packet.dart';

void main() {
  group('Packet encoding', () {
    test('encodes mouse move', () {
      final bytes = Packet.mouseMove(150, -200);
      expect(bytes.length, 5);
      expect(bytes[0], 0x01);
      final bd = ByteData.sublistView(bytes);
      expect(bd.getInt16(1), 150);
      expect(bd.getInt16(3), -200);
    });

    test('encodes scroll', () {
      final bytes = Packet.scroll(-3);
      expect(bytes.length, 3);
      expect(bytes[0], 0x02);
      final bd = ByteData.sublistView(bytes);
      expect(bd.getInt16(1), -3);
    });

    test('encodes left click', () {
      final bytes = Packet.leftClick(2);
      expect(bytes.length, 2);
      expect(bytes[0], 0x10);
      expect(bytes[1], 2);
    });

    test('encodes right click', () {
      final bytes = Packet.rightClick(2);
      expect(bytes.length, 2);
      expect(bytes[0], 0x11);
      expect(bytes[1], 2);
    });

    test('encodes double click', () {
      final bytes = Packet.doubleClick();
      expect(bytes.length, 1);
      expect(bytes[0], 0x12);
    });

    test('encodes key press', () {
      final bytes = Packet.keyPress(0x0041, 0);
      expect(bytes.length, 4);
      expect(bytes[0], 0x20);
      final bd = ByteData.sublistView(bytes);
      expect(bd.getUint16(1), 0x0041);
      expect(bytes[3], 0);
    });

    test('encodes key text', () {
      final bytes = Packet.keyText('hello');
      expect(bytes[0], 0x21);
      final bd = ByteData.sublistView(bytes);
      expect(bd.getUint16(1), 5);
      expect(String.fromCharCodes(bytes.sublist(3)), 'hello');
    });

    test('encodes media play pause', () {
      final bytes = Packet.mediaPlayPause();
      expect(bytes, [0x30]);
    });

    test('encodes media next', () {
      final bytes = Packet.mediaNext();
      expect(bytes, [0x31]);
    });

    test('encodes media prev', () {
      final bytes = Packet.mediaPrev();
      expect(bytes, [0x32]);
    });

    test('encodes volume up', () {
      final bytes = Packet.volumeUp();
      expect(bytes, [0x33]);
    });

    test('encodes volume down', () {
      final bytes = Packet.volumeDown();
      expect(bytes, [0x34]);
    });

    test('encodes volume mute', () {
      final bytes = Packet.volumeMute();
      expect(bytes, [0x35]);
    });

    test('wraps TCP packet with length prefix', () {
      final inner = Packet.leftClick(2);
      final wrapped = Packet.wrapTcp(inner);
      expect(wrapped.length, 4); // 2 bytes length + 2 bytes packet
      final bd = ByteData.sublistView(wrapped);
      expect(bd.getUint16(0), 2);
      expect(wrapped[2], 0x10);
      expect(wrapped[3], 2);
    });
  });
}
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd app && flutter test test/models/packet_test.dart`
Expected: FAIL — cannot find `package:openmouse/models/packet.dart`

- [ ] **Step 5: Implement packet model**

```dart
// app/lib/models/packet.dart
import 'dart:typed_data';
import 'dart:convert';

class Packet {
  static Uint8List mouseMove(int dx, int dy) {
    final bd = ByteData(5);
    bd.setUint8(0, 0x01);
    bd.setInt16(1, dx);
    bd.setInt16(3, dy);
    return bd.buffer.asUint8List();
  }

  static Uint8List scroll(int dy) {
    final bd = ByteData(3);
    bd.setUint8(0, 0x02);
    bd.setInt16(1, dy);
    return bd.buffer.asUint8List();
  }

  static Uint8List leftClick(int action) {
    return Uint8List.fromList([0x10, action]);
  }

  static Uint8List rightClick(int action) {
    return Uint8List.fromList([0x11, action]);
  }

  static Uint8List doubleClick() {
    return Uint8List.fromList([0x12]);
  }

  static Uint8List keyPress(int keyCode, int action) {
    final bd = ByteData(4);
    bd.setUint8(0, 0x20);
    bd.setUint16(1, keyCode);
    bd.setUint8(3, action);
    return bd.buffer.asUint8List();
  }

  static Uint8List keyText(String text) {
    final encoded = utf8.encode(text);
    final bd = ByteData(3 + encoded.length);
    bd.setUint8(0, 0x21);
    bd.setUint16(1, encoded.length);
    final bytes = bd.buffer.asUint8List();
    bytes.setRange(3, 3 + encoded.length, encoded);
    return bytes;
  }

  static Uint8List mediaPlayPause() => Uint8List.fromList([0x30]);
  static Uint8List mediaNext() => Uint8List.fromList([0x31]);
  static Uint8List mediaPrev() => Uint8List.fromList([0x32]);
  static Uint8List volumeUp() => Uint8List.fromList([0x33]);
  static Uint8List volumeDown() => Uint8List.fromList([0x34]);
  static Uint8List volumeMute() => Uint8List.fromList([0x35]);

  /// Wraps a TCP packet with a 2-byte big-endian length prefix.
  static Uint8List wrapTcp(Uint8List packet) {
    final bd = ByteData(2 + packet.length);
    bd.setUint16(0, packet.length);
    final bytes = bd.buffer.asUint8List();
    bytes.setRange(2, 2 + packet.length, packet);
    return bytes;
  }
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd app && flutter test test/models/packet_test.dart`
Expected: All 14 tests PASS

- [ ] **Step 7: Commit**

```bash
git add app/
git commit -m "feat(app): create Flutter project with packet model"
```

---

## Task 8: Flutter — Connection Service

**Files:**
- Create: `app/lib/services/connection_service.dart`
- Create: `app/test/services/connection_service_test.dart`

- [ ] **Step 1: Write failing test for connection service**

```dart
// app/test/services/connection_service_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:openmouse/services/connection_service.dart';

void main() {
  group('ConnectionService', () {
    test('initial state is disconnected', () {
      final service = ConnectionService();
      expect(service.isConnected, false);
    });

    test('serverIp is null when disconnected', () {
      final service = ConnectionService();
      expect(service.serverIp, null);
    });

    test('udpPort defaults to 19780', () {
      expect(ConnectionService.defaultUdpPort, 19780);
    });

    test('tcpPort defaults to 19781', () {
      expect(ConnectionService.defaultTcpPort, 19781);
    });
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && flutter test test/services/connection_service_test.dart`
Expected: FAIL

- [ ] **Step 3: Implement connection service**

```dart
// app/lib/services/connection_service.dart
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:openmouse/models/packet.dart';

class ConnectionService {
  static const int defaultUdpPort = 19780;
  static const int defaultTcpPort = 19781;

  RawDatagramSocket? _udpSocket;
  Socket? _tcpSocket;
  String? _serverIp;
  bool _connected = false;
  Timer? _reconnectTimer;

  final StreamController<bool> _connectionController =
      StreamController<bool>.broadcast();

  Stream<bool> get connectionStream => _connectionController.stream;
  bool get isConnected => _connected;
  String? get serverIp => _serverIp;

  Future<void> connect(String ip,
      {int udpPort = defaultUdpPort, int tcpPort = defaultTcpPort}) async {
    _serverIp = ip;

    _udpSocket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);

    _tcpSocket = await Socket.connect(ip, tcpPort);
    _tcpSocket!.listen(
      (_) {},
      onError: (_) => _handleDisconnect(),
      onDone: _handleDisconnect,
    );

    _connected = true;
    _connectionController.add(true);
  }

  void sendUdp(Uint8List data) {
    if (_udpSocket != null && _serverIp != null) {
      _udpSocket!.send(data, InternetAddress(_serverIp!), defaultUdpPort);
    }
  }

  void sendTcp(Uint8List data) {
    if (_tcpSocket != null) {
      _tcpSocket!.add(Packet.wrapTcp(data));
    }
  }

  void _handleDisconnect() {
    _connected = false;
    _connectionController.add(false);
    _startReconnect();
  }

  void _startReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
      if (_serverIp == null) return;
      try {
        await connect(_serverIp!);
        _reconnectTimer?.cancel();
      } catch (_) {
        // Will retry on next tick
      }
    });
  }

  Future<void> disconnect() async {
    _reconnectTimer?.cancel();
    _tcpSocket?.destroy();
    _udpSocket?.close();
    _tcpSocket = null;
    _udpSocket = null;
    _connected = false;
    _serverIp = null;
    _connectionController.add(false);
  }

  void dispose() {
    disconnect();
    _connectionController.close();
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && flutter test test/services/connection_service_test.dart`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/lib/services/connection_service.dart app/test/services/connection_service_test.dart
git commit -m "feat(app): add connection service for UDP and TCP"
```

---

## Task 9: Flutter — Discovery Service

**Files:**
- Create: `app/lib/services/discovery_service.dart`

- [ ] **Step 1: Implement discovery service**

```dart
// app/lib/services/discovery_service.dart
import 'dart:async';
import 'package:bonsoir/bonsoir.dart';

class DiscoveredServer {
  final String name;
  final String ip;
  final int tcpPort;
  final int udpPort;

  DiscoveredServer({
    required this.name,
    required this.ip,
    required this.tcpPort,
    required this.udpPort,
  });
}

class DiscoveryService {
  static const String serviceType = '_openmouse._tcp';

  BonsoirDiscovery? _discovery;
  final StreamController<List<DiscoveredServer>> _serversController =
      StreamController<List<DiscoveredServer>>.broadcast();
  final Map<String, DiscoveredServer> _servers = {};

  Stream<List<DiscoveredServer>> get serversStream => _serversController.stream;
  List<DiscoveredServer> get servers => _servers.values.toList();

  Future<void> startScan() async {
    _servers.clear();
    _discovery = BonsoirDiscovery(type: serviceType);
    await _discovery!.ready;

    _discovery!.eventStream!.listen((event) {
      if (event.type == BonsoirDiscoveryEventType.discoveryServiceResolved) {
        final service = event.service as ResolvedBonsoirService;
        final ip = service.host;
        if (ip == null) return;
        final udpPortStr = service.attributes['udp_port'];
        final udpPort =
            udpPortStr != null ? int.tryParse(udpPortStr) ?? 19780 : 19780;

        final server = DiscoveredServer(
          name: service.name,
          ip: ip,
          tcpPort: service.port,
          udpPort: udpPort,
        );
        _servers[ip] = server;
        _serversController.add(servers);
      } else if (event.type == BonsoirDiscoveryEventType.discoveryServiceLost) {
        final service = event.service;
        _servers.removeWhere((_, s) => s.name == service.name);
        _serversController.add(servers);
      }
    });

    await _discovery!.start();
  }

  Future<void> stopScan() async {
    await _discovery?.stop();
    _discovery = null;
  }

  void dispose() {
    stopScan();
    _serversController.close();
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add app/lib/services/discovery_service.dart
git commit -m "feat(app): add mDNS discovery service with bonsoir"
```

---

## Task 10: Flutter — Home Screen

**Files:**
- Create: `app/lib/screens/home_screen.dart`
- Modify: `app/lib/main.dart`

- [ ] **Step 1: Implement home screen**

```dart
// app/lib/screens/home_screen.dart
import 'package:flutter/material.dart';
import 'package:openmouse/services/discovery_service.dart';
import 'package:openmouse/services/connection_service.dart';
import 'package:openmouse/screens/control_screen.dart';

class HomeScreen extends StatefulWidget {
  final ConnectionService connectionService;

  const HomeScreen({super.key, required this.connectionService});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final DiscoveryService _discovery = DiscoveryService();
  final TextEditingController _ipController = TextEditingController();
  List<DiscoveredServer> _servers = [];
  bool _scanning = true;
  bool _connecting = false;

  @override
  void initState() {
    super.initState();
    _discovery.serversStream.listen((servers) {
      if (mounted) setState(() => _servers = servers);
    });
    _discovery.startScan();
  }

  @override
  void dispose() {
    _discovery.dispose();
    _ipController.dispose();
    super.dispose();
  }

  Future<void> _connectTo(String ip, {int udpPort = 19780, int tcpPort = 19781}) async {
    setState(() => _connecting = true);
    try {
      await widget.connectionService.connect(ip, udpPort: udpPort, tcpPort: tcpPort);
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => ControlScreen(
              connectionService: widget.connectionService,
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Connection failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _connecting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A2E),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 40),
              const Text(
                'OpenMouse',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Searching for servers...',
                style: TextStyle(color: Colors.grey[400], fontSize: 16),
              ),
              const SizedBox(height: 32),
              Expanded(
                child: _servers.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            CircularProgressIndicator(
                              color: Colors.green[400],
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'Looking for OpenMouse servers\non your network...',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: Colors.grey[500]),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        itemCount: _servers.length,
                        itemBuilder: (context, index) {
                          final server = _servers[index];
                          return Card(
                            color: const Color(0xFF16213E),
                            margin: const EdgeInsets.only(bottom: 12),
                            child: ListTile(
                              leading: Icon(
                                Icons.computer,
                                color: Colors.green[400],
                                size: 32,
                              ),
                              title: Text(
                                server.name,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              subtitle: Text(
                                server.ip,
                                style: TextStyle(color: Colors.grey[400]),
                              ),
                              trailing: const Icon(
                                Icons.arrow_forward_ios,
                                color: Colors.white54,
                                size: 16,
                              ),
                              onTap: () => _connectTo(
                                server.ip,
                                udpPort: server.udpPort,
                                tcpPort: server.tcpPort,
                              ),
                            ),
                          );
                        },
                      ),
              ),
              const Divider(color: Colors.white24),
              const SizedBox(height: 12),
              Text(
                'Connect manually',
                style: TextStyle(color: Colors.grey[400], fontSize: 14),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _ipController,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText: '192.168.1.100',
                        hintStyle: TextStyle(color: Colors.grey[600]),
                        filled: true,
                        fillColor: const Color(0xFF16213E),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                          borderSide: BorderSide.none,
                        ),
                      ),
                      keyboardType: TextInputType.numberWithOptions(decimal: true),
                    ),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton(
                    onPressed: _connecting
                        ? null
                        : () {
                            final ip = _ipController.text.trim();
                            if (ip.isNotEmpty) _connectTo(ip);
                          },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green[400],
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 24,
                        vertical: 16,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                    child: _connecting
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Text('Connect'),
                  ),
                ],
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Update main.dart**

```dart
// app/lib/main.dart
import 'package:flutter/material.dart';
import 'package:openmouse/services/connection_service.dart';
import 'package:openmouse/screens/home_screen.dart';

void main() {
  runApp(const OpenMouseApp());
}

class OpenMouseApp extends StatefulWidget {
  const OpenMouseApp({super.key});

  @override
  State<OpenMouseApp> createState() => _OpenMouseAppState();
}

class _OpenMouseAppState extends State<OpenMouseApp> {
  final ConnectionService _connectionService = ConnectionService();

  @override
  void dispose() {
    _connectionService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'OpenMouse',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        colorScheme: ColorScheme.dark(
          primary: Colors.green[400]!,
        ),
      ),
      home: HomeScreen(connectionService: _connectionService),
    );
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add app/lib/main.dart app/lib/screens/home_screen.dart
git commit -m "feat(app): add home screen with server discovery and manual IP"
```

---

## Task 11: Flutter — Trackpad Widget

**Files:**
- Create: `app/lib/widgets/trackpad.dart`

- [ ] **Step 1: Implement trackpad widget**

```dart
// app/lib/widgets/trackpad.dart
import 'package:flutter/material.dart';
import 'package:openmouse/models/packet.dart';
import 'package:openmouse/services/connection_service.dart';

class Trackpad extends StatefulWidget {
  final ConnectionService connectionService;

  const Trackpad({super.key, required this.connectionService});

  @override
  State<Trackpad> createState() => _TrackpadState();
}

class _TrackpadState extends State<Trackpad> {
  // Sensitivity multiplier for mouse movement
  static const double _sensitivity = 1.5;
  // Sensitivity for scroll
  static const double _scrollSensitivity = 0.5;

  // Accumulated scroll delta for threshold-based sending
  double _scrollAccumulator = 0.0;

  void _onPanUpdate(DragUpdateDetails details) {
    final dx = (details.delta.dx * _sensitivity).round();
    final dy = (details.delta.dy * _sensitivity).round();
    if (dx != 0 || dy != 0) {
      widget.connectionService.sendUdp(Packet.mouseMove(dx, dy));
    }
  }

  void _onTap() {
    widget.connectionService.sendTcp(Packet.leftClick(2));
  }

  void _onDoubleTap() {
    widget.connectionService.sendTcp(Packet.doubleClick());
  }

  void _onLongPress() {
    widget.connectionService.sendTcp(Packet.rightClick(2));
  }

  void _onScrollUpdate(DragUpdateDetails details) {
    _scrollAccumulator += details.delta.dy * _scrollSensitivity;
    final scrollAmount = _scrollAccumulator.truncate();
    if (scrollAmount != 0) {
      widget.connectionService.sendUdp(Packet.scroll(-scrollAmount));
      _scrollAccumulator -= scrollAmount;
    }
  }

  void _onTwoFingerScroll(ScaleUpdateDetails details) {
    if (details.pointerCount < 2) return;
    final dy = (details.focalPointDelta.dy * _scrollSensitivity).round();
    if (dy != 0) {
      widget.connectionService.sendUdp(Packet.scroll(-dy));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        // Trackpad area (85%)
        Expanded(
          flex: 85,
          child: GestureDetector(
            onPanUpdate: _onPanUpdate,
            onTap: _onTap,
            onDoubleTap: _onDoubleTap,
            onLongPress: _onLongPress,
            onScaleUpdate: _onTwoFingerScroll,
            child: Container(
              decoration: BoxDecoration(
                color: const Color(0xFF16213E),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Center(
                child: Icon(
                  Icons.touch_app,
                  size: 48,
                  color: Colors.grey[700],
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: 8),
        // Scroll bar (15%)
        Expanded(
          flex: 15,
          child: GestureDetector(
            onVerticalDragUpdate: _onScrollUpdate,
            child: Container(
              decoration: BoxDecoration(
                color: const Color(0xFF0F3460),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.keyboard_arrow_up, color: Colors.grey[500]),
                  const SizedBox(height: 8),
                  Icon(Icons.unfold_more, color: Colors.grey[500], size: 32),
                  const SizedBox(height: 8),
                  Icon(Icons.keyboard_arrow_down, color: Colors.grey[500]),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add app/lib/widgets/trackpad.dart
git commit -m "feat(app): add trackpad widget with scroll bar"
```

---

## Task 12: Flutter — Keyboard Input Widget

**Files:**
- Create: `app/lib/widgets/keyboard_input.dart`

- [ ] **Step 1: Implement keyboard input widget**

```dart
// app/lib/widgets/keyboard_input.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:openmouse/models/packet.dart';
import 'package:openmouse/services/connection_service.dart';

class KeyboardInput extends StatefulWidget {
  final ConnectionService connectionService;

  const KeyboardInput({super.key, required this.connectionService});

  @override
  State<KeyboardInput> createState() => _KeyboardInputState();
}

class _KeyboardInputState extends State<KeyboardInput> {
  final TextEditingController _textController = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _keyboardVisible = false;

  @override
  void dispose() {
    _textController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _toggleKeyboard() {
    setState(() {
      _keyboardVisible = !_keyboardVisible;
      if (_keyboardVisible) {
        _focusNode.requestFocus();
      } else {
        _focusNode.unfocus();
      }
    });
  }

  void _sendText() {
    final text = _textController.text;
    if (text.isNotEmpty) {
      widget.connectionService.sendTcp(Packet.keyText(text));
      _textController.clear();
    }
  }

  void _onKey(KeyEvent event) {
    final keyCode = event.logicalKey.keyId & 0xFFFF;
    if (event is KeyDownEvent) {
      widget.connectionService.sendTcp(Packet.keyPress(keyCode, 0));
    } else if (event is KeyUpEvent) {
      widget.connectionService.sendTcp(Packet.keyPress(keyCode, 1));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          // Text input field + send button
          Row(
            children: [
              Expanded(
                child: KeyboardListener(
                  focusNode: _focusNode,
                  onKeyEvent: _onKey,
                  child: TextField(
                    controller: _textController,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: 'Type text to send...',
                      hintStyle: TextStyle(color: Colors.grey[600]),
                      filled: true,
                      fillColor: const Color(0xFF16213E),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: BorderSide.none,
                      ),
                    ),
                    onSubmitted: (_) => _sendText(),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                onPressed: _sendText,
                icon: Icon(Icons.send, color: Colors.green[400]),
                style: IconButton.styleFrom(
                  backgroundColor: const Color(0xFF16213E),
                  padding: const EdgeInsets.all(16),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          // Open keyboard button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _toggleKeyboard,
              icon: Icon(
                _keyboardVisible ? Icons.keyboard_hide : Icons.keyboard,
              ),
              label: Text(
                _keyboardVisible ? 'Hide Keyboard' : 'Open Keyboard',
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF0F3460),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
          ),
          const Spacer(),
          // Hint text
          Text(
            'Key presses are sent in real-time.\nUse the text field to type and send phrases.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey[600], fontSize: 13),
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add app/lib/widgets/keyboard_input.dart
git commit -m "feat(app): add keyboard input widget"
```

---

## Task 13: Flutter — Media Controls Widget

**Files:**
- Create: `app/lib/widgets/media_controls.dart`

- [ ] **Step 1: Implement media controls widget**

```dart
// app/lib/widgets/media_controls.dart
import 'package:flutter/material.dart';
import 'package:openmouse/models/packet.dart';
import 'package:openmouse/services/connection_service.dart';

class MediaControls extends StatelessWidget {
  final ConnectionService connectionService;

  const MediaControls({super.key, required this.connectionService});

  void _send(Uint8ListCallback builder) {
    connectionService.sendTcp(builder());
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Playback controls
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _MediaButton(
                icon: Icons.skip_previous_rounded,
                size: 56,
                onTap: () => connectionService.sendTcp(Packet.mediaPrev()),
              ),
              _MediaButton(
                icon: Icons.play_arrow_rounded,
                size: 80,
                primary: true,
                onTap: () => connectionService.sendTcp(Packet.mediaPlayPause()),
              ),
              _MediaButton(
                icon: Icons.skip_next_rounded,
                size: 56,
                onTap: () => connectionService.sendTcp(Packet.mediaNext()),
              ),
            ],
          ),
          const SizedBox(height: 48),
          // Volume controls
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _MediaButton(
                icon: Icons.volume_down_rounded,
                size: 56,
                onTap: () => connectionService.sendTcp(Packet.volumeDown()),
              ),
              _MediaButton(
                icon: Icons.volume_off_rounded,
                size: 56,
                onTap: () => connectionService.sendTcp(Packet.volumeMute()),
              ),
              _MediaButton(
                icon: Icons.volume_up_rounded,
                size: 56,
                onTap: () => connectionService.sendTcp(Packet.volumeUp()),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

typedef Uint8ListCallback = List<int> Function();

class _MediaButton extends StatelessWidget {
  final IconData icon;
  final double size;
  final bool primary;
  final VoidCallback onTap;

  const _MediaButton({
    required this.icon,
    required this.size,
    this.primary = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: primary ? Colors.green[400] : const Color(0xFF16213E),
          shape: BoxShape.circle,
        ),
        child: Icon(
          icon,
          color: primary ? Colors.white : Colors.grey[300],
          size: size * 0.5,
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add app/lib/widgets/media_controls.dart
git commit -m "feat(app): add media controls widget"
```

---

## Task 14: Flutter — Control Screen + Navigation

**Files:**
- Create: `app/lib/screens/control_screen.dart`

- [ ] **Step 1: Implement control screen**

```dart
// app/lib/screens/control_screen.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:openmouse/services/connection_service.dart';
import 'package:openmouse/screens/home_screen.dart';
import 'package:openmouse/widgets/trackpad.dart';
import 'package:openmouse/widgets/keyboard_input.dart';
import 'package:openmouse/widgets/media_controls.dart';

class ControlScreen extends StatefulWidget {
  final ConnectionService connectionService;

  const ControlScreen({super.key, required this.connectionService});

  @override
  State<ControlScreen> createState() => _ControlScreenState();
}

class _ControlScreenState extends State<ControlScreen> {
  int _currentIndex = 0;
  late StreamSubscription<bool> _connectionSub;

  @override
  void initState() {
    super.initState();
    _connectionSub = widget.connectionService.connectionStream.listen((connected) {
      if (!connected && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Connection lost. Reconnecting...'),
            backgroundColor: Colors.orange,
          ),
        );
      }
    });
  }

  @override
  void dispose() {
    _connectionSub.cancel();
    super.dispose();
  }

  void _disconnect() {
    widget.connectionService.disconnect();
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) => HomeScreen(connectionService: widget.connectionService),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      Trackpad(connectionService: widget.connectionService),
      KeyboardInput(connectionService: widget.connectionService),
      MediaControls(connectionService: widget.connectionService),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFF1A1A2E),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1A2E),
        elevation: 0,
        title: Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: widget.connectionService.isConnected
                    ? Colors.green[400]
                    : Colors.orange,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              widget.connectionService.serverIp ?? 'OpenMouse',
              style: const TextStyle(fontSize: 16),
            ),
          ],
        ),
        actions: [
          IconButton(
            onPressed: _disconnect,
            icon: const Icon(Icons.close),
            tooltip: 'Disconnect',
          ),
        ],
      ),
      body: pages[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        backgroundColor: const Color(0xFF16213E),
        selectedItemColor: Colors.green[400],
        unselectedItemColor: Colors.grey[600],
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.touch_app),
            label: 'Trackpad',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.keyboard),
            label: 'Keyboard',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.music_note),
            label: 'Media',
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 2: Run the app to verify navigation works**

Run: `cd app && flutter run`
Expected: App launches, shows home screen. After connecting to server, shows control screen with bottom navigation between trackpad, keyboard, and media.

- [ ] **Step 3: Commit**

```bash
git add app/lib/screens/control_screen.dart
git commit -m "feat(app): add control screen with bottom navigation"
```

---

## Task 15: End-to-End Integration Test

**Files:** No new files

- [ ] **Step 1: Run all server tests**

Run: `cd server && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run all Flutter tests**

Run: `cd app && flutter test`
Expected: All tests PASS

- [ ] **Step 3: Manual end-to-end test**

1. Start server: `cd server && python openmouse.py`
2. Install app on Android device: `cd app && flutter run`
3. Verify: app discovers server, connect, move mouse, tap for click, scroll bar works, type text, media buttons work
4. Verify: tray icon shows connected status

- [ ] **Step 4: Commit any fixes from integration testing**

```bash
git add -A && git commit -m "fix: integration test fixes"
```

---

## Task 16: PyInstaller Packaging

**Files:**
- Create: `server/openmouse.spec` (auto-generated)

- [ ] **Step 1: Install PyInstaller**

Run: `cd server && pip install pyinstaller`

- [ ] **Step 2: Build executable**

Run: `cd server && pyinstaller --onefile --add-data "icon.png:." --name openmouse --windowed openmouse.py`

- [ ] **Step 3: Test the packaged executable**

Run: `cd server/dist && ./openmouse` (Linux) or `openmouse.exe` (Windows)
Expected: Server starts with tray icon, same behavior as running with Python

- [ ] **Step 4: Commit the spec file**

```bash
git add server/openmouse.spec
git commit -m "feat(server): add PyInstaller packaging config"
```
