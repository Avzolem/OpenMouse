# server/tray.py
import threading
import logging
from pathlib import Path
from PIL import Image
import pystray

logger = logging.getLogger("openmouse.tray")


class Tray:
    def __init__(self, ip: str, on_quit, on_uninstall=None):
        self._ip = ip
        self._on_quit = on_quit
        self._on_uninstall = on_uninstall
        self._icon = None
        self._thread = None
        self._status = "Esperando conexion..."

    def set_status(self, status: str):
        self._status = status
        if self._icon:
            self._icon.update_menu()

    def notify(self, title: str, message: str) -> bool:
        """Muestra un globo desde el icono. Devuelve si el backend lo acepto.

        pystray toma (mensaje, titulo) en ese orden, y no todos los backends
        implementan notify(): AppIndicator en Linux lanza NotImplementedError.
        """
        if not self._icon:
            return False
        self._icon.notify(message, title)
        return True

    def start(self):
        icon_path = Path(__file__).parent / "icon.png"
        image = Image.open(icon_path)

        menu_items = [
            pystray.MenuItem(f"IP: {self._ip}", None, enabled=False),
            pystray.MenuItem(lambda _: self._status, None, enabled=False),
            pystray.Menu.SEPARATOR,
        ]
        if self._on_uninstall:
            menu_items.append(pystray.MenuItem("Desinstalar", self._uninstall))
        menu_items.append(pystray.MenuItem("Salir", self._quit))

        self._icon = pystray.Icon(
            "openmouse",
            image,
            "OpenMouse",
            menu=pystray.Menu(*menu_items),
        )
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()
        logger.info("System tray started")

    def _quit(self, icon, item):
        icon.stop()
        self._on_quit()

    def _uninstall(self, icon, item):
        icon.stop()
        if self._on_uninstall:
            self._on_uninstall()

    def stop(self):
        if self._icon:
            self._icon.stop()
