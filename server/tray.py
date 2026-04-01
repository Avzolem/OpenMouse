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
