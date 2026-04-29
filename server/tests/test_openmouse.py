import sys
import importlib
from unittest.mock import patch, MagicMock
import pytest


# Stub out GUI/platform modules that are unavailable in the test environment
# before openmouse is imported.
_GUI_STUBS = ["pystray", "tray", "PIL", "PIL.Image"]


@pytest.fixture(autouse=True)
def stub_gui_modules():
    """Inject lightweight stubs for GUI modules so openmouse can be imported."""
    added = {}
    for mod in _GUI_STUBS:
        if mod not in sys.modules:
            added[mod] = MagicMock()
            sys.modules[mod] = added[mod]
    # Also ensure tray.Tray exists
    sys.modules["tray"].Tray = MagicMock()
    yield
    # Remove any stubs we injected; also evict openmouse so each test gets a
    # fresh import with the right sys.platform monkeypatch applied.
    for mod in added:
        del sys.modules[mod]
    if "openmouse" in sys.modules:
        del sys.modules["openmouse"]


class TestEnsureInstalled:
    def test_returns_early_on_linux(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        import openmouse
        monkeypatch.setattr(openmouse, "get_install_dir", lambda: tmp_path / "install")
        with patch.object(openmouse.shutil, "copy2") as mock_copy, \
             patch.object(openmouse, "_register_autostart") as mock_reg:
            assert openmouse.ensure_installed() is None
            mock_copy.assert_not_called()
            mock_reg.assert_not_called()

    def test_returns_early_on_macos(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        import openmouse
        monkeypatch.setattr(openmouse, "get_install_dir", lambda: tmp_path / "install")
        with patch.object(openmouse, "_register_autostart") as mock_reg:
            assert openmouse.ensure_installed() is None
            mock_reg.assert_not_called()


class TestRegisterAutostart:
    def test_returns_early_on_linux(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        import openmouse
        openmouse._register_autostart(tmp_path / "openmouse")
        assert not (tmp_path / ".config" / "autostart" / "openmouse.desktop").exists()


class TestUninstallLinux:
    def test_schedules_detached_removal_of_install_dir(self, tmp_path, monkeypatch):
        install_dir = tmp_path / "openmouse"
        install_dir.mkdir()
        (install_dir / "openmouse").write_text("fake binary")

        # The current uninstall() builds the desktop path as
        # Path.home() / ".config" / "autostart" / "openmouse.desktop",
        # so create it at the same location relative to our fake home.
        autostart = tmp_path / ".config" / "autostart" / "openmouse.desktop"
        autostart.parent.mkdir(parents=True)
        autostart.write_text("entry")

        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr("openmouse.get_install_dir", lambda: install_dir)
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        captured = []
        def fake_popen(cmd, **kwargs):
            captured.append((cmd, kwargs))
            return MagicMock()
        monkeypatch.setattr("subprocess.Popen", fake_popen)

        from openmouse import uninstall
        uninstall()

        # Autostart entry removed inline
        assert not autostart.exists()

        # Detached deletion scheduled
        assert len(captured) == 1
        cmd, kwargs = captured[0]
        assert cmd[0] == "sh"
        assert cmd[1] == "-c"
        assert "rm -rf" in cmd[2]
        assert str(install_dir) in cmd[2]
        assert kwargs.get("start_new_session") is True

    def test_no_op_when_nothing_installed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr("openmouse.get_install_dir", lambda: tmp_path / "missing")
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        called = []
        monkeypatch.setattr(
            "subprocess.Popen",
            lambda cmd, **kw: called.append(cmd) or MagicMock(),
        )

        from openmouse import uninstall
        uninstall()  # should not raise
        assert called == []  # no removal scheduled if dir doesn't exist
