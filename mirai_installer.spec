# -*- mode: python ; coding: utf-8 -*-
#
# MirAI_OS PyInstaller spec file
# Build with:  pyinstaller mirai_installer.spec
#
# Produces:  dist/MirAI_OS_Installer.exe  (Windows)
#            dist/MirAI_OS_Installer      (Linux/macOS)

import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821  (SPECPATH provided by PyInstaller)

block_cipher = None

a = Analysis(
    [str(ROOT / "installer_main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Bundle the entire application source so the installer can launch it
        (str(ROOT / "main.py"),           "."),
        (str(ROOT / "config.py"),         "."),
        (str(ROOT / "requirements.txt"),  "."),
        (str(ROOT / "modules"),           "modules"),
        (str(ROOT / "mod2"),              "mod2"),
    ],
    hiddenimports=[
        # tkinter is usually auto-detected, but list submodules explicitly
        "tkinter",
        "tkinter.ttk",
        "tkinter.scrolledtext",
        "tkinter.font",
        "tkinter.messagebox",
        # Core modules
        "modules.llm_engine",
        "modules.telegram_bot",
        "modules.voice_io",
        "modules.agent_flows",
        "modules.self_modification",
        "modules.kali_integration",
        "modules.ssh_connector",
        "modules.context_optimizer",
        # Mod 2
        "mod2.advanced_agent",
        "mod2.memory_system",
        "mod2.web_scraper",
        # Optional runtime deps (import may fail gracefully)
        "pyttsx3",
        "speech_recognition",
        "telegram",
        "telegram.ext",
        "paramiko",
        "duckduckgo_search",
        "requests",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "cv2",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "setuptools",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MirAI_OS_Installer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # GUI mode – no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,           # Provide an .ico path here to customise the icon
    # Windows version info (optional)
    version=None,
)
