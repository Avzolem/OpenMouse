# -*- mode: python ; coding: utf-8 -*-
import sys

from PyInstaller.utils.hooks import collect_submodules

# pynput elige su backend con importlib en tiempo de ejecucion, asi que el
# analisis estatico de PyInstaller no ve ninguno y el binario muere nada mas
# arrancar con "ImportError: this platform is not supported".
#
# Los nombres van escritos a mano a proposito: collect_submodules("pynput")
# IMPORTA el paquete, y el __init__ de pynput ya hace esa seleccion de backend
# al importarse, asi que en una maquina de compilacion sin DISPLAY revienta.
# Tapar eso con un try/except deja la lista vacia y produce exactamente el
# binario roto que se pretendia evitar.
if sys.platform == "win32":
    _pynput = [
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        "pynput._util.win32",
        "pynput._util.win32_vks",
    ]
    _xlib = []
    _tray = []
elif sys.platform == "darwin":
    _pynput = [
        "pynput.keyboard._darwin",
        "pynput.mouse._darwin",
        "pynput._util.darwin",
        "pynput._util.darwin_vks",
    ]
    _xlib = []
    _tray = []
else:
    _pynput = [
        "pynput.keyboard._xorg",
        "pynput.keyboard._uinput",
        "pynput.mouse._xorg",
        "pynput._util.xorg",
        "pynput._util.xorg_keysyms",
        "pynput._util.uinput",
    ]
    # python-xlib carga sus extensiones de protocolo por nombre. Si esto
    # fallase, que falle el build: es preferible a publicar un binario que no
    # arranca.
    _xlib = collect_submodules("Xlib")

    # El hook de pystray hace collect_submodules("pystray"), que IMPORTA cada
    # backend al compilar. pystray._util.gtk llama a Gtk.init_check() al
    # importarse y sin DISPLAY (o sin PyGObject) lanza ImportError, asi que
    # appindicator y gtk quedaban fuera en silencio y el binario caia en el
    # backend xorg, que no tiene menu: el icono no hacia nada al pulsarlo. Van
    # escritos a mano por la misma razon que los de pynput.
    _tray = [
        "pystray._appindicator",
        "pystray._gtk",
        "pystray._xorg",
        "pystray._util.gtk",
        "pystray._util.notify_dbus",
        "gi.repository.Gtk",
        "gi.repository.AyatanaAppIndicator3",
    ]
    # Sin PyGObject o sin las typelibs, PyInstaller no encuentra nada que
    # empaquetar y publica otra vez el binario sin menu. Mejor que falle aqui.
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("AyatanaAppIndicator3", "0.1")
    except (ImportError, ValueError) as exc:
        raise SystemExit(
            "OpenMouse: el icono de bandeja necesita PyGObject y las typelibs "
            f"de Gtk 3 y AyatanaAppIndicator3 para compilar ({exc})."
        )

hiddenimports = _pynput + [
    "pynput.keyboard._dummy",
    "pynput.mouse._dummy",
] + _xlib + _tray


a = Analysis(
    ['openmouse.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.png', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    # Gtk 3 es la que usa pystray; sin fijarla el hook de gi puede elegir otra.
    # Iconos, temas e idiomas se limitan para no inflar el binario con todo lo
    # que tenga instalado la maquina de compilacion.
    hooksconfig={
        "gi": {
            "module-versions": {"Gtk": "3.0"},
            "icons": ["Adwaita"],
            "themes": ["Adwaita"],
            "languages": ["es", "en_US"],
        },
    },
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='openmouse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
