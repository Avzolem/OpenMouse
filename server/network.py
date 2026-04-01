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
