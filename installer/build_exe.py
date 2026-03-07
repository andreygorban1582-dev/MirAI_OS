"""
MirAI OS — PyInstaller Build Script
Run this on Windows to compile MirAI_OS.exe

Usage:
    pip install pyinstaller
    python installer/build_exe.py

Output: dist/MirAI_OS.exe (single-file, no install needed)
"""
import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
SPEC_FILE = Path(__file__).parent / "MirAI_OS.spec"


def build():
    print("[FUTURE GADGET LAB] Building MirAI_OS.exe...")

    # Check PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                        # Single .exe
        "--windowed",                       # No console window (has its own terminal)
        "--name", "MirAI_OS",
        "--add-data", f"{ROOT / 'config'}:config",
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.scrolledtext",
        "--hidden-import", "tkinter.ttk",
        "--icon", str(Path(__file__).parent / "icon.ico") if (Path(__file__).parent / "icon.ico").exists() else "NONE",
        "--clean",
        str(Path(__file__).parent / "mirai_launcher.py"),
    ]

    # Remove NONE if no icon
    cmd = [c for c in cmd if c != "NONE"]

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(ROOT), check=True)

    # Move output
    exe_src = ROOT / "dist" / "MirAI_OS.exe"
    exe_dst = ROOT / "MirAI_OS.exe"
    if exe_src.exists():
        shutil.copy2(exe_src, exe_dst)
        print(f"\n[✓] Built: {exe_dst}")
        print("  Share this single file — double-click to launch MirAI OS!")
    else:
        print("[✗] Build may have failed — check output above.")


if __name__ == "__main__":
    build()
