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
    def __init__(self):
        self._mouse = mouse_controller
        self._keyboard = keyboard_controller
        # Teclas y botones que hemos pulsado y aun no soltado. Si el movil
        # pierde la red entre el press y el release, nadie enviara el release y
        # la tecla se queda hundida en el PC del usuario.
        self._held_keys = set()
        self._held_buttons = set()

    def move(self, dx: int, dy: int):
        self._mouse.move(dx, dy)

    def scroll(self, dy: int):
        self._mouse.scroll(0, dy)

    def click(self, button: str, action: int):
        btn = Button.left if button == "left" else Button.right
        if action == 0:
            self._mouse.press(btn)
            self._held_buttons.add(btn)
        elif action == 1:
            self._mouse.release(btn)
            self._held_buttons.discard(btn)
        elif action == 2:
            self._mouse.click(btn, 1)

    def double_click(self):
        self._mouse.click(Button.left, 2)

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
        try:
            if action == 0:
                self._keyboard.press(key)
                self._held_keys.add(key)
            elif action == 1:
                self._keyboard.release(key)
                self._held_keys.discard(key)
        except Exception:
            # Una tecla que el backend no acepta no debe tumbar la conexion.
            logger.warning(f"no se pudo enviar la tecla {key_code}", exc_info=True)

    def release_all(self):
        """Suelta todo lo que quedo pulsado. Se llama cuando se va el cliente."""
        for key in list(self._held_keys):
            try:
                self._keyboard.release(key)
            except Exception:
                logger.warning(f"no se pudo soltar la tecla {key!r}", exc_info=True)
        self._held_keys.clear()

        for button in list(self._held_buttons):
            try:
                self._mouse.release(button)
            except Exception:
                logger.warning(f"no se pudo soltar el boton {button!r}", exc_info=True)
        self._held_buttons.clear()

    def type_text(self, text: str):
        try:
            self._keyboard.type(text)
        except Exception:
            logger.warning("no se pudo escribir el texto", exc_info=True)

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
            self._keyboard.press(key)
            self._keyboard.release(key)
