"""
Windows .exe Installer Builder — MirAI_OS

Uses PyInstaller to create a standalone Windows executable.
Run this script on Windows: python installer/build_exe.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def build() -> None:
    try:
        import PyInstaller  # noqa: F401, PLC0415
    except ImportError:
        print("PyInstaller not found. Installing…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    [r'{BASE_DIR / "main.py"}'],
    pathex=[r'{BASE_DIR}'],
    binaries=[],
    datas=[
        (r'{BASE_DIR / "config" / "legion_go_profile.json"}', 'config'),
        (r'{BASE_DIR / ".env.example"}', '.'),
    ],
    hiddenimports=[
        'pydantic_settings',
        'tiktoken',
        'httpx',
        'aiohttp',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='MirAI_OS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon=None,
)
"""

    spec_path = BASE_DIR / "installer" / "mirai_os.spec"
    spec_path.write_text(spec_content)

    dist_dir = BASE_DIR / "installer" / "dist"
    dist_dir.mkdir(exist_ok=True)

    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        "--distpath", str(dist_dir),
        "--workpath", str(BASE_DIR / "installer" / "build"),
        str(spec_path),
    ])

    print(f"\n✅ Installer built at: {dist_dir / 'MirAI_OS.exe'}")


if __name__ == "__main__":
    if sys.platform != "win32":
        print("⚠️  Building .exe is only supported on Windows.")
        print("   To cross-compile, use Wine or a Windows CI runner.")
        sys.exit(0)
    build()
