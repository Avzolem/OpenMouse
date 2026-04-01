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
