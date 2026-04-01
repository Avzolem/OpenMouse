from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

mouse_controller = MouseController()
keyboard_controller = KeyboardController()


class InputHandler:
    def __init__(self):
        self._mouse = mouse_controller
        self._keyboard = keyboard_controller

    def move(self, dx: int, dy: int):
        self._mouse.move(dx, dy)

    def scroll(self, dy: int):
        self._mouse.scroll(0, dy)

    def click(self, button: str, action: int):
        btn = Button.left if button == "left" else Button.right
        if action == 0:
            self._mouse.press(btn)
        elif action == 1:
            self._mouse.release(btn)
        elif action == 2:
            self._mouse.click(btn, 1)

    def double_click(self):
        self._mouse.click(Button.left, 2)

    def key_press(self, key_code: int, action: int):
        try:
            char = chr(key_code)
        except (ValueError, OverflowError):
            return
        if action == 0:
            self._keyboard.press(char)
        elif action == 1:
            self._keyboard.release(char)

    def type_text(self, text: str):
        self._keyboard.type(text)

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
