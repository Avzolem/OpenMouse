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
from tray import Tray
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
            subprocess.Popen(
                ["sh", "-c", f'sleep 2 && rm -rf "{install_dir}"'],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"Scheduled removal of: {install_dir}")

    logger.info("OpenMouse uninstalled.")


async def run_server():
    handler = InputHandler()
    udp_server = UdpServer(handler, port=UDP_PORT)
    tcp_server = TcpServer(handler, port=TCP_PORT)
    discovery = Discovery(tcp_port=TCP_PORT, udp_port=UDP_PORT)

    stop_event = asyncio.Event()
    should_uninstall = False

    def quit_app():
        stop_event.set()

    def uninstall_and_quit():
        nonlocal should_uninstall
        should_uninstall = True
        stop_event.set()

    ip = discovery.start()
    logger.info(f"OpenMouse server running at {ip}")

    tray = Tray(ip, on_quit=quit_app, on_uninstall=uninstall_and_quit)

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
