"""
installer/build_installer.py
─────────────────────────────
Build a standalone Windows .exe using PyInstaller.
═════════════════════════════════════════════════════════════════════════════
WHAT THIS DOES
──────────────
• Runs PyInstaller on main.py to produce a single-file Windows executable.
• The .exe bundles the entire Python environment so users don't need to
  install Python separately.
• Sets the icon and version metadata for the resulting binary.

USAGE (run on Windows inside the virtual environment):
    python installer/build_installer.py

Output:
    dist/MirAI.exe
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "main.py"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
ICON = ROOT / "assets" / "mirai.ico"  # optional – won't fail if missing

args = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--onefile",
    "--name",
    "MirAI",
    "--distpath",
    str(DIST),
    "--workpath",
    str(BUILD),
    "--specpath",
    str(BUILD),
    "--noconfirm",
    "--clean",
    # Add data files
    f"--add-data={ROOT / 'config'}:config",
    f"--add-data={ROOT / '.env.example'}:.env.example",
    # Hidden imports not auto-detected by PyInstaller
    "--hidden-import=mirai",
    "--hidden-import=mirai.agent",
    "--hidden-import=mirai.llm",
    "--hidden-import=mirai.memory",
    "--hidden-import=mirai.anonymity",
    "--hidden-import=mirai.github_client",
    "--hidden-import=mirai.self_mod",
    "--hidden-import=mirai.telegram_bot",
    "--hidden-import=mirai.voice",
    "--hidden-import=mirai.kali_tools",
    "--hidden-import=mirai.ssh_connector",
    "--hidden-import=mirai.settings",
]

if ICON.exists():
    args.extend(["--icon", str(ICON)])

args.append(str(MAIN))

print(f"Building MirAI.exe from {MAIN}…")
result = subprocess.run(args, cwd=ROOT)

if result.returncode == 0:
    print(f"\n✅ Build succeeded: {DIST / 'MirAI.exe'}")
else:
    print("\n❌ Build failed – see output above.")
    sys.exit(1)
