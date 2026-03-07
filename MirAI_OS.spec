# -*- mode: python ; coding: utf-8 -*-
# MirAI_OS PyInstaller spec file
# Build with: pyinstaller MirAI_OS.spec

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["ai/main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("config.yaml", "."),
        ("mods", "mods"),
        ("ai", "ai"),
    ],
    hiddenimports=[
        # openai
        "openai",
        "openai._models",
        "openai.resources",
        # yaml
        "yaml",
        # voice
        "pyttsx3",
        "pyttsx3.drivers",
        "pyttsx3.drivers.sapi5",
        "speech_recognition",
        "whisper",
        # telegram
        "telegram",
        "telegram.ext",
        # windows
        "win32api",
        "win32con",
        "win32gui",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MirAI_OS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,           # Set False for windowed GUI (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Request UAC elevation on Windows
    uac_admin=True,
    icon="assets/icon.ico" if Path("assets/icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MirAI_OS",
)
