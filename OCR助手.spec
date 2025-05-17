# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['F:\\py\\ydcb-auto-master\\gui.py'],
    pathex=[],
    binaries=[],
    datas=[('logs', 'logs')],
    hiddenimports=['PIL._tkinter', 'win32gui', 'win32con', 'win32api', 'paddle', 'paddleocr'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OCR助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OCR助手',
)
