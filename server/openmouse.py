# server/openmouse.py
import asyncio
import logging
import os
import shutil
import sys
from pathlib import Path

from input_handler import InputHandler
from network import UdpServer, TcpServer
from discovery import Discovery
from protocol import UDP_PORT, TCP_PORT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("openmouse")

APP_NAME = "OpenMouse"
REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_install_dir() -> Path:
    """Returns %APPDATA%/OpenMouse on Windows, ~/.local/share/openmouse on Linux."""
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / APP_NAME
    return Path.home() / ".local" / "share" / "openmouse"


def get_exe_path() -> Path:
    """Returns the path of the currently running executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return Path(__file__).resolve()


def is_installed() -> bool:
    """Check if OpenMouse is already installed in its install directory."""
    install_dir = get_install_dir()
    if getattr(sys, "frozen", False):
        return get_exe_path().resolve().is_relative_to(install_dir.resolve())
    return False


def ensure_installed():
    """Install silently if not already running from install dir. Returns installed exe path. Windows-only — Linux is handled by scripts/install.sh."""
    if sys.platform != "win32":
        return None

    install_dir = get_install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)

    src = get_exe_path()

    if getattr(sys, "frozen", False):
        dest = install_dir / src.name
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
            logger.info(f"Installed to: {dest}")
        else:
            dest = src
    else:
        dest = src

    icon_src = Path(__file__).parent / "icon.png"
    icon_dest = install_dir / "icon.png"
    if icon_src.exists() and icon_src.resolve() != icon_dest.resolve():
        shutil.copy2(icon_src, icon_dest)

    _register_autostart(dest)
    return dest


def _register_autostart(exe_path: Path):
    """Register the executable to start on login. Windows-only — Linux is handled by scripts/install.sh."""
    if sys.platform != "win32":
        return
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, str(exe_path))
    winreg.CloseKey(key)
    logger.info("Registered in Windows startup.")


def uninstall():
    """Remove auto-start entry and schedule file deletion on exit."""
    if sys.platform == "win32":
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, APP_NAME)
            winreg.CloseKey(key)
            logger.info("Removed from Windows startup.")
        except FileNotFoundError:
            pass

        # Schedule self-deletion via a batch script that waits for us to exit
        install_dir = get_install_dir()
        if install_dir.exists():
            bat_path = Path(os.environ.get("TEMP", ".")) / "openmouse_uninstall.bat"
            bat_path.write_text(
                f'@echo off\n'
                f'timeout /t 2 /nobreak >nul\n'
                f'rmdir /s /q "{install_dir}"\n'
                f'del "%~f0"\n',
                encoding="utf-8",
            )
            import subprocess
            subprocess.Popen(
                ["cmd", "/c", str(bat_path)],
                creationflags=0x00000008,  # DETACHED_PROCESS
            )
            logger.info(f"Scheduled removal of: {install_dir}")
    else:
        desktop_entry = Path.home() / ".config" / "autostart" / "openmouse.desktop"
        if desktop_entry.exists():
            desktop_entry.unlink()
            logger.info("Removed from Linux autostart.")

        install_dir = get_install_dir()
        if install_dir.exists():
            # Schedule detached removal so we can delete the directory we're
            # currently running from. Mirrors the Windows .bat pattern.
            import subprocess
            # La ruta va como argumento, no interpolada en el script: asi una
            # ruta con comillas no puede alterar el comando.
            subprocess.Popen(
                ["sh", "-c", 'sleep 2; rm -rf "$1"', "sh", str(install_dir)],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"Scheduled removal of: {install_dir}")

    logger.info("OpenMouse uninstalled.")


def threadsafe_callback(loop, fn):
    """Envuelve fn para poder invocarla desde otro hilo.

    Los menus de pystray corren en el hilo del tray. Llamar ahi a
    stop_event.set() marca el Event pero NO despierta al event loop, que sigue
    dormido en el selector hasta que llegue trafico de red — asi que Quit no
    cerraba el servidor. call_soon_threadsafe si lo despierta.
    """
    def callback(*_args, **_kwargs):
        loop.call_soon_threadsafe(fn)

    return callback


async def run_server():
    loop = asyncio.get_running_loop()
    handler = InputHandler()
    udp_server = UdpServer(handler, port=UDP_PORT)
    tcp_server = TcpServer(handler, port=TCP_PORT)
    discovery = Discovery(tcp_port=TCP_PORT, udp_port=UDP_PORT)

    stop_event = asyncio.Event()
    should_uninstall = False

    def _request_stop():
        stop_event.set()

    def _request_uninstall():
        nonlocal should_uninstall
        should_uninstall = True
        stop_event.set()

    # El tray invoca estos callbacks desde su propio hilo.
    quit_app = threadsafe_callback(loop, _request_stop)
    uninstall_and_quit = threadsafe_callback(loop, _request_uninstall)

    ip = await discovery.start_async()
    logger.info(f"OpenMouse server running at {ip}")

    # El tray es opcional: en un escritorio sin GTK/appindicator, pystray falla
    # al importarse. Eso no debe impedir controlar el PC desde el movil, que es
    # lo que hace la aplicacion.
    tray = None
    try:
        from tray import Tray

        tray = Tray(ip, on_quit=quit_app, on_uninstall=uninstall_and_quit)
    except Exception:
        logger.warning(
            "Sin icono en la bandeja del sistema; el servidor sigue activo. "
            "Para pararlo, cierra el proceso.",
            exc_info=True,
        )

    def on_connect(addr):
        if tray:
            tray.set_status(f"Connected: {addr[0]}")

    def on_disconnect(addr):
        if tray:
            tray.set_status("Waiting for connection...")

    tcp_server.on_client_connected = on_connect
    tcp_server.on_client_disconnected = on_disconnect

    try:
        await udp_server.start()
        await tcp_server.start()
    except OSError:
        logger.exception(
            f"No se pudieron abrir los puertos UDP:{UDP_PORT} / TCP:{TCP_PORT}. "
            "Probablemente ya hay otra instancia de OpenMouse en marcha."
        )
        await udp_server.stop()
        await tcp_server.stop()
        discovery.stop()
        return

    if tray:
        try:
            tray.start()
        except Exception:
            logger.warning("No se pudo arrancar el icono de bandeja", exc_info=True)
            tray = None

    logger.info(f"Listening — UDP:{UDP_PORT} TCP:{TCP_PORT}")

    try:
        await stop_event.wait()
    finally:
        # Pase lo que pase (Ctrl+C incluido), soltamos puertos y mDNS.
        if tray:
            tray.stop()
        await udp_server.stop()
        await tcp_server.stop()
        discovery.stop()

    if should_uninstall:
        uninstall()

    logger.info("OpenMouse stopped")


if __name__ == "__main__":
    # Auto-install on first run, then start server
    ensure_installed()
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass
