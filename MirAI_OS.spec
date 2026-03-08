# -*- mode: python ; coding: utf-8 -*-
# ─── MirAI_OS  –  PyInstaller spec ──────────────────────────────────────────
from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('.env.example', '.'),
        ('mods', 'mods'),
    ],
    hiddenimports=[
        'telegram',
        'telegram.ext',
        'httpx',
        'edge_tts',
        'speech_recognition',
        'pyaudio',
        'paramiko',
        'dotenv',
        'asyncio',
        'pydantic',
        'redis',
        'mods',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch',
        'transformers',
        'tensorflow',
        'cv2',
        'matplotlib',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MirAI_OS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
