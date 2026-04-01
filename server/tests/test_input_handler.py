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
