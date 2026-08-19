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


class TestMultipleClients:
    """El tray refleja el estado de conexion: no debe anunciar 'desconectado'
    mientras siga habiendo algun cliente activo."""

    @pytest.mark.asyncio
    async def test_disconnect_callback_only_fires_when_last_client_leaves(self):
        from network import TcpServer
        handler = MagicMock()
        server = TcpServer(handler, host="127.0.0.1", port=0)
        events = []
        server.on_client_connected = lambda addr: events.append("conn")
        server.on_client_disconnected = lambda addr: events.append("disc")
        await server.start()
        try:
            _, w1 = await asyncio.open_connection("127.0.0.1", server.port)
            _, w2 = await asyncio.open_connection("127.0.0.1", server.port)
            await asyncio.sleep(0.1)
            assert events == ["conn", "conn"]

            w2.close()
            await asyncio.sleep(0.15)
            assert events == ["conn", "conn"], "el cliente 1 sigue conectado"

            w1.close()
            await asyncio.sleep(0.15)
            assert events == ["conn", "conn", "disc"]
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_stop_returns_even_with_a_client_connected(self):
        """Parar el servidor con el movil conectado es el caso normal al pulsar
        Quit; wait_closed() espera a los handlers, asi que hay que cortarlos."""
        from network import TcpServer
        server = TcpServer(MagicMock(), host="127.0.0.1", port=0)
        await server.start()
        _, writer = await asyncio.open_connection("127.0.0.1", server.port)
        await asyncio.sleep(0.1)
        try:
            await asyncio.wait_for(server.stop(), timeout=5)
        except asyncio.TimeoutError:
            pytest.fail("TcpServer.stop() no retorna con un cliente conectado")
        finally:
            writer.close()

    @pytest.mark.asyncio
    async def test_typing_long_text_does_not_block_the_event_loop(self):
        """Escribir una frase es sincrono en pynput; si corre en el loop, el
        cursor se congela mientras dura."""
        import time
        from network import TcpServer

        handler = MagicMock()
        handler.type_text.side_effect = lambda text: time.sleep(0.4)
        server = TcpServer(handler, host="127.0.0.1", port=0)
        await server.start()
        _, writer = await asyncio.open_connection("127.0.0.1", server.port)
        try:
            payload = b"\x21" + struct.pack("!H", 5) + b"hola!"
            writer.write(struct.pack("!H", len(payload)) + payload)
            await writer.drain()

            # El loop debe seguir atendiendo otras tareas mientras se teclea.
            start = time.monotonic()
            await asyncio.sleep(0.15)
            assert time.monotonic() - start < 0.35

            await asyncio.sleep(0.5)
            handler.type_text.assert_called_once_with("hola!")
        finally:
            writer.close()
            await server.stop()

    @pytest.mark.asyncio
    async def test_held_keys_are_released_when_the_last_client_leaves(self):
        """El movil que pierde el WiFi tras un KeyDown nunca mandara el KeyUp."""
        from network import TcpServer

        handler = MagicMock()
        server = TcpServer(handler, host="127.0.0.1", port=0)
        await server.start()
        _, writer = await asyncio.open_connection("127.0.0.1", server.port)
        await asyncio.sleep(0.1)
        try:
            payload = struct.pack("!bHb", 0x20, ord("a"), 0)  # KEY_PRESS down
            writer.write(struct.pack("!H", len(payload)) + payload)
            await writer.drain()
            await asyncio.sleep(0.1)
            handler.release_all.assert_not_called()

            writer.close()
            await asyncio.sleep(0.2)
            handler.release_all.assert_called_once()
        finally:
            await server.stop()
