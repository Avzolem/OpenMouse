from unittest.mock import MagicMock, patch, call
import pytest
from input_handler import InputHandler


@pytest.fixture
def handler():
    with patch("input_handler.mouse_controller") as mock_mouse, \
         patch("input_handler.keyboard_controller") as mock_kb:
        h = InputHandler()
        h._mouse = mock_mouse
        h._keyboard = mock_kb
        yield h


class TestMouseMove:
    def test_move(self, handler):
        handler.move(10, -5)
        handler._mouse.move.assert_called_once_with(10, -5)


class TestScroll:
    def test_scroll_up(self, handler):
        handler.scroll(-3)
        handler._mouse.scroll.assert_called_once_with(0, -3)

    def test_scroll_down(self, handler):
        handler.scroll(5)
        handler._mouse.scroll.assert_called_once_with(0, 5)


class TestClick:
    def test_left_click(self, handler):
        with patch("input_handler.Button") as MockButton:
            handler.click("left", 2)
            handler._mouse.click.assert_called_once_with(MockButton.left, 1)

    def test_left_press(self, handler):
        with patch("input_handler.Button") as MockButton:
            handler.click("left", 0)
            handler._mouse.press.assert_called_once_with(MockButton.left)

    def test_left_release(self, handler):
        with patch("input_handler.Button") as MockButton:
            handler.click("left", 1)
            handler._mouse.release.assert_called_once_with(MockButton.left)

    def test_right_click(self, handler):
        with patch("input_handler.Button") as MockButton:
            handler.click("right", 2)
            handler._mouse.click.assert_called_once_with(MockButton.right, 1)

    def test_double_click(self, handler):
        with patch("input_handler.Button") as MockButton:
            handler.double_click()
            handler._mouse.click.assert_called_once_with(MockButton.left, 2)


class TestMedia:
    def test_play_pause(self, handler):
        with patch("input_handler.Key") as MockKey:
            handler.media("play_pause")
            handler._keyboard.press.assert_called_once_with(MockKey.media_play_pause)
            handler._keyboard.release.assert_called_once_with(MockKey.media_play_pause)

    def test_volume_up(self, handler):
        with patch("input_handler.Key") as MockKey:
            handler.media("volume_up")
            handler._keyboard.press.assert_called_once_with(MockKey.media_volume_up)
            handler._keyboard.release.assert_called_once_with(MockKey.media_volume_up)


class TestKeyText:
    def test_type_text(self, handler):
        handler.type_text("hello")
        handler._keyboard.type.assert_called_once_with("hello")


class TestResolveKey:
    def test_printable_characters_pass_through(self):
        from input_handler import InputHandler
        handler = InputHandler()
        assert handler.resolve_key(ord("a")) == "a"
        assert handler.resolve_key(ord("ñ")) == "ñ"

    def test_special_codes_map_to_real_keys(self):
        from pynput.keyboard import Key
        from input_handler import InputHandler
        from protocol import SPECIAL_KEYS
        handler = InputHandler()
        assert handler.resolve_key(SPECIAL_KEYS["enter"]) == Key.enter
        assert handler.resolve_key(SPECIAL_KEYS["up"]) == Key.up
        assert handler.resolve_key(SPECIAL_KEYS["shift"]) == Key.shift
        assert handler.resolve_key(SPECIAL_KEYS["f1"]) == Key.f1

    def test_every_special_code_resolves(self):
        from input_handler import InputHandler
        from protocol import SPECIAL_KEYS
        handler = InputHandler()
        for name, code in SPECIAL_KEYS.items():
            assert handler.resolve_key(code) is not None, name

    def test_unmapped_private_use_codes_are_dropped_not_typed(self):
        from input_handler import InputHandler
        handler = InputHandler()
        assert handler.resolve_key(0xE0FF) is None
        assert handler.resolve_key(0x0007) is None

    def test_key_press_survives_a_failing_backend(self):
        from unittest.mock import MagicMock
        from input_handler import InputHandler
        handler = InputHandler()
        handler._keyboard = MagicMock()
        handler._keyboard.press.side_effect = ValueError("backend roto")
        handler.key_press(ord("a"), 0)  # no debe propagar


class TestReleaseAll:
    """Si el movil pierde el WiFi despues de un KeyDown, nadie enviara el
    KeyUp: la tecla se queda pulsada en el PC del usuario."""

    def test_releases_keys_still_held(self):
        from unittest.mock import MagicMock
        from input_handler import InputHandler
        from protocol import SPECIAL_KEYS

        handler = InputHandler()
        handler._keyboard = MagicMock()
        handler.key_press(ord("a"), 0)
        handler.key_press(SPECIAL_KEYS["shift"], 0)
        handler._keyboard.release.reset_mock()

        handler.release_all()

        assert handler._keyboard.release.call_count == 2

    def test_does_not_release_keys_already_released(self):
        from unittest.mock import MagicMock
        from input_handler import InputHandler

        handler = InputHandler()
        handler._keyboard = MagicMock()
        handler.key_press(ord("a"), 0)
        handler.key_press(ord("a"), 1)
        handler._keyboard.release.reset_mock()

        handler.release_all()

        handler._keyboard.release.assert_not_called()

    def test_releases_mouse_buttons_still_held(self):
        from unittest.mock import MagicMock
        from input_handler import InputHandler

        handler = InputHandler()
        handler._mouse = MagicMock()
        handler.click("left", 0)  # press sin release
        handler._mouse.release.reset_mock()

        handler.release_all()

        handler._mouse.release.assert_called_once()

    def test_is_safe_to_call_twice(self):
        from unittest.mock import MagicMock
        from input_handler import InputHandler

        handler = InputHandler()
        handler._keyboard = MagicMock()
        handler.key_press(ord("a"), 0)
        handler.release_all()
        handler._keyboard.release.reset_mock()
        handler.release_all()
        handler._keyboard.release.assert_not_called()
