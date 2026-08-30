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
elif sys.platform == "darwin":
    _pynput = [
        "pynput.keyboard._darwin",
        "pynput.mouse._darwin",
        "pynput._util.darwin",
        "pynput._util.darwin_vks",
    ]
    _xlib = []
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

hiddenimports = _pynput + [
    "pynput.keyboard._dummy",
    "pynput.mouse._dummy",
] + _xlib


a = Analysis(
    ['openmouse.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.png', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
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
