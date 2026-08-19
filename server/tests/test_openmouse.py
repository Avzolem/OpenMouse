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
        # La ruta viaja como argumento, no interpolada en el script: asi una
        # ruta con comillas no puede alterar el comando.
        assert str(install_dir) not in cmd[2]
        assert str(install_dir) in cmd[3:]
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


class TestThreadsafeStop:
    """El menu del tray corre en su propio hilo; parar el servidor desde ahi
    tiene que despertar al event loop, no solo marcar el Event."""

    def test_callback_wakes_a_sleeping_event_loop(self):
        import asyncio
        import importlib
        import threading
        import time

        openmouse = importlib.import_module("openmouse")

        async def scenario():
            loop = asyncio.get_running_loop()
            stop_event = asyncio.Event()
            stop_from_tray = openmouse.threadsafe_callback(loop, stop_event.set)

            # Sin trafico de red que despierte al selector, un stop_event.set()
            # normal desde otro hilo dejaria el loop dormido hasta el timeout.
            threading.Thread(
                target=lambda: (time.sleep(0.1), stop_from_tray()),
                daemon=True,
            ).start()

            start = time.monotonic()
            await asyncio.wait_for(stop_event.wait(), timeout=3)
            return time.monotonic() - start

        elapsed = asyncio.run(scenario())
        assert elapsed < 1.0, f"el loop tardo {elapsed:.2f}s en despertar"


class TestEnsureInstalledWindows:
    """En Windows la instalacion solo debe ocurrir desde un exe congelado."""

    def test_dev_run_does_not_register_autostart(self, tmp_path, monkeypatch):
        import importlib

        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        openmouse = importlib.import_module("openmouse")
        monkeypatch.setattr(openmouse, "get_install_dir", lambda: tmp_path / "inst")

        called = []
        monkeypatch.setattr(openmouse, "_register_autostart", lambda p: called.append(p))

        assert openmouse.ensure_installed() is None
        assert called == []
        assert not (tmp_path / "inst").exists()

    def test_survives_a_locked_destination_exe(self, tmp_path, monkeypatch):
        """Windows no deja sobrescribir la imagen de un proceso en marcha."""
        import importlib

        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        openmouse = importlib.import_module("openmouse")

        install_dir = tmp_path / "inst"
        install_dir.mkdir()
        (install_dir / "openmouse.exe").write_text("instalado")
        src = tmp_path / "descargas" / "openmouse.exe"
        src.parent.mkdir()
        src.write_text("nuevo")

        monkeypatch.setattr(openmouse, "get_install_dir", lambda: install_dir)
        monkeypatch.setattr(openmouse, "get_exe_path", lambda: src)
        monkeypatch.setattr(openmouse.shutil, "copy2", MagicMock(side_effect=PermissionError))
        registered = []
        monkeypatch.setattr(openmouse, "_register_autostart", lambda p: registered.append(p))

        dest = openmouse.ensure_installed()

        assert dest == install_dir / "openmouse.exe"
        assert registered == [dest]
