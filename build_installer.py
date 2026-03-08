#!/usr/bin/env python3
"""
build_installer.py – MirAI_OS PyInstaller helper
==================================================
Convenience wrapper around PyInstaller that ensures the correct working
directory and spec file are used.

Usage (from the repository root):

    # Default – use the bundled spec file:
    python build_installer.py

    # Pass extra PyInstaller options:
    python build_installer.py --clean --noconfirm

The resulting executable is written to:
    dist/MirAI_OS.exe  (Windows)
    dist/MirAI_OS      (Linux / macOS)
"""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).parent.resolve()
    spec_file = repo_root / "MirAI_OS.spec"

    if not spec_file.exists():
        print(f"[build_installer] ERROR: spec file not found: {spec_file}", file=sys.stderr)
        return 1

    cmd = [sys.executable, "-m", "pyinstaller", str(spec_file)] + sys.argv[1:]
    print(f"[build_installer] Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=repo_root)
    if result.returncode == 0:
        exe_suffix = ".exe" if sys.platform == "win32" else ""
        print(
            f"\n[build_installer] Build succeeded.\n"
            f"  Executable: dist/MirAI_OS{exe_suffix}\n"
        )
    else:
        print(f"\n[build_installer] Build FAILED (exit code {result.returncode}).", file=sys.stderr)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
