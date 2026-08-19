import logging

from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

from protocol import SPECIAL_KEY_NAMES

logger = logging.getLogger("openmouse.input")

# Nombre en el protocolo -> tecla de pynput.
_PYNPUT_KEYS = {
    "enter": Key.enter,
    "backspace": Key.backspace,
    "tab": Key.tab,
    "escape": Key.esc,
    "delete": Key.delete,
    "insert": Key.insert,
    "home": Key.home,
    "end": Key.end,
    "page_up": Key.page_up,
    "page_down": Key.page_down,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "shift": Key.shift,
    "shift_r": Key.shift_r,
    "ctrl": Key.ctrl,
    "ctrl_r": Key.ctrl_r,
    "alt": Key.alt,
    "alt_r": Key.alt_r,
    "cmd": Key.cmd,
    "cmd_r": Key.cmd_r,
    "caps_lock": Key.caps_lock,
    "f1": Key.f1,
    "f2": Key.f2,
    "f3": Key.f3,
    "f4": Key.f4,
    "f5": Key.f5,
    "f6": Key.f6,
    "f7": Key.f7,
    "f8": Key.f8,
    "f9": Key.f9,
    "f10": Key.f10,
    "f11": Key.f11,
    "f12": Key.f12,
}

mouse_controller = MouseController()
keyboard_controller = KeyboardController()


class InputHandler:
    """Envia eventos de entrada al SO.

    Ningun fallo del backend (X11 caido, sesion bloqueada, tecla que el layout
    no acepta) debe propagarse: estos metodos se llaman desde el event loop y
    desde el callback de UDP, donde una excepcion tumba la conexion o llena el
    log con un traceback por datagrama a 60-100 Hz.
    """

    def __init__(self):
        self._mouse = mouse_controller
        self._keyboard = keyboard_controller
        # Teclas y botones que hemos pulsado y aun no soltado. Si el movil
        # pierde la red entre el press y el release, nadie enviara el release y
        # la tecla se queda hundida en el PC del usuario.
        self._held_keys = set()
        self._held_buttons = set()
        self._backend_failed = False

    def _safe(self, description, action):
        try:
            action()
        except Exception:
            # Solo se avisa una vez: a 60-100 Hz, un backend caido inundaria
            # el log con el mismo traceback.
            if not self._backend_failed:
                self._backend_failed = True
                logger.warning(
                    f"el backend de entrada rechazo '{description}'; "
                    "se omiten los avisos siguientes",
                    exc_info=True,
                )
            else:
                logger.debug(f"fallo de entrada: {description}")

    def move(self, dx: int, dy: int):
        self._safe("move", lambda: self._mouse.move(dx, dy))

    def scroll(self, dy: int):
        self._safe("scroll", lambda: self._mouse.scroll(0, dy))

    def click(self, button: str, action: int):
        btn = Button.left if button == "left" else Button.right
        if action == 0:
            self._safe("press", lambda: self._mouse.press(btn))
            self._held_buttons.add(btn)
        elif action == 1:
            self._safe("release", lambda: self._mouse.release(btn))
            self._held_buttons.discard(btn)
        elif action == 2:
            self._safe("click", lambda: self._mouse.click(btn, 1))

    def double_click(self):
        self._safe("double_click", lambda: self._mouse.click(Button.left, 2))

    def resolve_key(self, key_code: int):
        """Traduce un key_code del protocolo a algo que pynput sepa pulsar.

        Devuelve None si el codigo no es tecleable: sin esto, una flecha o un
        Shift acababan como chr(772) / chr(258) y el servidor escribia basura.
        """
        name = SPECIAL_KEY_NAMES.get(key_code)
        if name is not None:
            return _PYNPUT_KEYS.get(name)
        if key_code < 0x20 or 0xE000 <= key_code <= 0xF8FF:
            return None
        try:
            return chr(key_code)
        except (ValueError, OverflowError):
            return None

    def key_press(self, key_code: int, action: int):
        key = self.resolve_key(key_code)
        if key is None:
            logger.debug(f"key_code sin mapeo, ignorado: {key_code}")
            return
        if action == 0:
            self._safe(f"key_press {key_code}", lambda: self._keyboard.press(key))
            self._held_keys.add(key)
        elif action == 1:
            self._safe(f"key_release {key_code}", lambda: self._keyboard.release(key))
            self._held_keys.discard(key)

    def release_all(self):
        """Suelta todo lo que quedo pulsado. Se llama cuando se va el cliente."""
        for key in list(self._held_keys):
            self._safe(f"release {key!r}", lambda k=key: self._keyboard.release(k))
        self._held_keys.clear()

        for button in list(self._held_buttons):
            self._safe(f"release {button!r}", lambda b=button: self._mouse.release(b))
        self._held_buttons.clear()

    def type_text(self, text: str):
        self._safe("type_text", lambda: self._keyboard.type(text))

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
            self._safe(f"media {command}", lambda: (
                self._keyboard.press(key), self._keyboard.release(key)
            ))
