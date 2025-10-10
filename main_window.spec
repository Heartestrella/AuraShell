# -*- mode: python ; coding: utf-8 -*-
import os

data_files = [('resource', 'resource'), ('tools/updater.py', 'tools')]
if os.path.exists('version.txt'):
    data_files.append(('version.txt', '.'))

a = Analysis(
    ['main_window.py'],
    pathex=[],
    binaries=[],
    datas=data_files,
    hiddenimports=['tzdata', 'scipy.special._cdflib'],
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
    [],
    exclude_binaries=True,
    name='main_window',
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
    icon=['resource\\icons\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main_window',
)
