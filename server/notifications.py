# server/notifications.py
"""Avisos de escritorio cuando el movil se conecta.

Cada plataforma tiene su via y ninguna esta garantizada, asi que se prueban en
orden y se cae a la siguiente:

- Windows: un toast por WinRT lanzado con PowerShell. El globo del icono de
  bandeja NO sirve aqui: Shell_NotifyIcon devuelve exito pero Windows 10/11
  descarta el aviso si la aplicacion no tiene un AppUserModelID registrado.
  Comprobado en Windows 11: pystray devuelve True y no aparece ninguna ventana.
- Linux: `notify-send` (libnotify), presente en casi cualquier escritorio.
- Como ultimo recurso, el globo del tray, que en algun entorno si funciona.

Un aviso que falla no puede tumbar el servidor ni congelar el event loop, asi
que todo va envuelto y los procesos externos se lanzan en un hilo aparte.
"""
import base64
import logging
import shutil
import subprocess
import sys
import threading
from pathlib import Path

logger = logging.getLogger("openmouse.notifications")

# El backend puede fallar en cada aviso; se avisa una vez y luego se calla.
_warned = False

# En un exe compilado sin consola, lanzar PowerShell abriria una ventana negra.
_CREATE_NO_WINDOW = 0x08000000

# AppUserModelID de PowerShell: ya viene registrado en todo Windows, asi que
# sirve de emisor sin tener que instalar un acceso directo propio.
_POWERSHELL_APP_ID = (
    "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe"
)

# El texto viaja por variables de entorno: asi no hay que escapar comillas ni
# se puede colar nada raro en el script.
_TOAST_SCRIPT = """
$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
    [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$nodes = $xml.GetElementsByTagName('text')
$nodes.Item(0).AppendChild($xml.CreateTextNode($env:OPENMOUSE_TOAST_TITLE)) > $null
$nodes.Item(1).AppendChild($xml.CreateTextNode($env:OPENMOUSE_TOAST_MESSAGE)) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('APP_ID').Show($toast)
"""


def is_windows() -> bool:
    return sys.platform == "win32"


def icon_path() -> Path:
    """icon.png, tanto en un exe de PyInstaller como ejecutando desde fuente."""
    base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(__file__).parent
    return base / "icon.png"


def _run_detached(argv, env_extra=None):
    """Lanza el notificador sin bloquear el loop y sin dejar zombis."""
    import os

    env = None
    if env_extra:
        env = os.environ.copy()
        env.update(env_extra)
    creationflags = _CREATE_NO_WINDOW if is_windows() else 0

    def worker():
        try:
            subprocess.run(
                argv,
                timeout=20,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                env=env,
                creationflags=creationflags,
            )
        except (OSError, subprocess.SubprocessError):
            logger.debug("fallo el notificador externo", exc_info=True)

    threading.Thread(target=worker, name="notify", daemon=True).start()


def _toast_windows(title: str, message: str) -> bool:
    if not is_windows():
        return False
    exe = shutil.which("powershell") or shutil.which("powershell.exe")
    if not exe:
        return False
    script = _TOAST_SCRIPT.replace("APP_ID", _POWERSHELL_APP_ID)
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    _run_detached(
        [exe, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        env_extra={
            "OPENMOUSE_TOAST_TITLE": title,
            "OPENMOUSE_TOAST_MESSAGE": message,
        },
    )
    return True


def _notify_send(title: str, message: str) -> bool:
    if is_windows():
        return False
    exe = shutil.which("notify-send")
    if not exe:
        return False
    argv = [exe, "--app-name=OpenMouse"]
    icon = icon_path()
    if icon.exists():
        argv.append(f"--icon={icon}")
    argv.extend([title, message])
    _run_detached(argv)
    return True


def _tray_balloon(title: str, message: str, tray) -> bool:
    if tray is None:
        return False
    return bool(tray.notify(title, message))


def notify(title: str, message: str, tray=None) -> bool:
    """Muestra un aviso. Devuelve si algun backend lo acepto.

    Que no haya ninguno no es un error: el servidor sigue funcionando igual y
    la conexion queda en el registro.
    """
    global _warned
    backends = (
        (_toast_windows, _notify_send)
        if is_windows()
        else (_notify_send, _toast_windows)
    )
    for backend in backends:
        try:
            if backend(title, message):
                return True
        except Exception:
            logger.debug("backend de avisos fallo: %s", backend.__name__, exc_info=True)

    try:
        if _tray_balloon(title, message, tray):
            return True
    except Exception:
        logger.debug("el tray no pudo notificar", exc_info=True)

    if not _warned:
        _warned = True
        logger.info(
            "Sin sistema de avisos disponible; las conexiones solo se veran "
            "en el registro."
        )
    return False
