import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _icon_class(module):
    """Una clase Icon falsa que se hace pasar por el backend ``module``."""
    return type(
        "Icon",
        (),
        {
            "__module__": module,
            "__init__": lambda self, *args, **kwargs: None,
            "run": lambda self: None,
            "stop": lambda self: None,
            "update_menu": lambda self: None,
        },
    )


@pytest.fixture
def tray_module(monkeypatch):
    """Importa tray.py con pystray y PIL sustituidos, y lo descarta al final."""
    fake_pystray = MagicMock()
    fake_pil = MagicMock()
    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    monkeypatch.setitem(sys.modules, "PIL", fake_pil)
    monkeypatch.setitem(sys.modules, "PIL.Image", fake_pil.Image)
    monkeypatch.delitem(sys.modules, "tray", raising=False)
    import tray

    yield tray, fake_pystray
    sys.modules.pop("tray", None)


class TestBackendName:
    @pytest.mark.parametrize(
        "module, expected",
        [
            ("pystray._appindicator", "appindicator"),
            ("pystray._gtk", "gtk"),
            ("pystray._xorg", "xorg"),
            ("pystray._win32", "win32"),
        ],
    )
    def test_reads_the_backend_from_the_icon_class(self, tray_module, module, expected):
        tray, _ = tray_module
        assert tray.backend_name(_icon_class(module)) == expected


class TestStartLogsTheBackend:
    """Con el backend xorg el icono aparece pero no tiene menu; el log tiene
    que dejarlo claro para no volver a perseguirlo a ciegas."""

    def _start(self, tray_module, module):
        tray, fake_pystray = tray_module
        fake_pystray.Icon = _icon_class(module)
        icon = tray.Tray("192.168.1.2", on_quit=lambda: None)
        icon.start()
        icon._thread.join(timeout=1)

    def test_appindicator_is_logged_without_warning(self, tray_module, caplog):
        caplog.set_level("INFO", logger="openmouse.tray")
        self._start(tray_module, "pystray._appindicator")
        assert "backend: appindicator" in caplog.text
        assert not [r for r in caplog.records if r.levelname == "WARNING"]

    def test_xorg_warns_that_there_is_no_menu(self, tray_module, caplog):
        caplog.set_level("INFO", logger="openmouse.tray")
        self._start(tray_module, "pystray._xorg")
        assert "backend: xorg" in caplog.text
        assert [r for r in caplog.records if r.levelname == "WARNING"]


class TestSpecBundlesTheTrayBackends:
    """El hook de pystray importa los backends al compilar y sin pantalla
    descarta appindicator en silencio; el spec debe nombrarlos a mano."""

    def test_linux_spec_lists_the_menu_capable_backends(self):
        spec = (Path(__file__).parents[1] / "openmouse.spec").read_text()
        for name in (
            "pystray._appindicator",
            "pystray._util.gtk",
            "gi.repository.Gtk",
            "gi.repository.AyatanaAppIndicator3",
        ):
            assert f'"{name}"' in spec, f"falta {name} en openmouse.spec"
