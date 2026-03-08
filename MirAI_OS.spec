# MirAI_OS.spec – PyInstaller build specification
# ================================================
# Build a standalone executable with:
#   pip install pyinstaller
#   pyinstaller MirAI_OS.spec
#
# The resulting executable will be at:
#   dist/MirAI_OS.exe  (Windows)
#   dist/MirAI_OS      (Linux / macOS)

from PyInstaller.building.api import EXE, PYZ
from PyInstaller.building.build_main import Analysis

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Include the mods system and persona definitions
        ('mods.py', '.'),
        ('lab_personas.py', '.'),
        ('orchestrator.py', '.'),
    ],
    hiddenimports=[
        # Telegram
        'telegram',
        'telegram.ext',
        # HTTP
        'httpx',
        # TTS / STT
        'edge_tts',
        'speech_recognition',
        'pyaudio',
        # SSH
        'paramiko',
        # Environment
        'dotenv',
        # Kubernetes (optional)
        'kubernetes',
        # Async
        'asyncio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy ML frameworks unless needed
        'torch',
        'transformers',
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
    console=True,     # Keep console open (CLI mode); set False for GUI
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
