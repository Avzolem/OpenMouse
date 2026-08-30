# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

# pynput elige el backend por plataforma con importlib en tiempo de ejecucion
# (pynput.keyboard._xorg, ._win32, ...), asi que el analisis estatico de
# PyInstaller no ve ninguno y el binario muere al importar con
# "ImportError: this platform is not supported". Lo mismo vale para python-xlib,
# que carga sus extensiones de protocolo por nombre.
def _submodules(package):
    """Recoge submodulos tolerando que el paquete no exista en esta plataforma.

    python-xlib solo se instala en Linux; en el runner de Windows no esta y no
    puede tumbar el build.
    """
    try:
        return collect_submodules(package)
    except Exception:
        return []


hiddenimports = _submodules("pynput") + _submodules("Xlib")


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
