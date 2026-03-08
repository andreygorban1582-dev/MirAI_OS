"""Build MirAI_OS standalone executable via PyInstaller."""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent
SPEC_FILE = REPO_ROOT / "MirAI_OS.spec"


def main() -> None:
    if not SPEC_FILE.exists():
        print(f"[!] Spec file not found: {SPEC_FILE}")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        str(SPEC_FILE),
    ]
    print(f"[build] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        print("[!] Build failed.")
        sys.exit(result.returncode)

    exe = REPO_ROOT / "dist" / (
        "MirAI_OS.exe" if sys.platform == "win32" else "MirAI_OS"
    )
    if exe.exists():
        print(f"[+] Build successful: {exe}")
    else:
        print("[!] Executable not found after build.")


if __name__ == "__main__":
    main()
