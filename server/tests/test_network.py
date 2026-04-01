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
