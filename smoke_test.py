#!/usr/bin/env python3
"""
smoke_test.py – MirAI_OS startup smoke-test
=============================================
Validates that the application (either the built executable or the Python
source entry-point) can start and display its help/usage text without
crashing.  Designed to run in CI or as a quick sanity check after a build.

Usage:

    # Test the Python source entry-point (works on any OS):
    python smoke_test.py

    # Test the built executable (Windows):
    python smoke_test.py --exe dist/MirAI_OS.exe

    # Test the built executable (Linux / macOS):
    python smoke_test.py --exe dist/MirAI_OS

Exit codes:
    0 – success
    1 – process launched but produced unexpected output or non-zero exit
    2 – process could not be started (file not found, permission error, etc.)
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_smoke_test(target: list[str], timeout: int = 30) -> int:
    """
    Run *target* with ``--help`` and verify it exits cleanly.

    Returns 0 on success, non-zero on failure.
    """
    cmd = target + ["--help"]
    print(f"[smoke_test] Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        print(
            f"[smoke_test] ERROR: executable not found – '{cmd[0]}'",
            file=sys.stderr,
        )
        return 2
    except subprocess.TimeoutExpired:
        print(
            f"[smoke_test] ERROR: process timed out after {timeout}s.",
            file=sys.stderr,
        )
        return 1
    except PermissionError:
        print(
            f"[smoke_test] ERROR: permission denied – '{cmd[0]}'",
            file=sys.stderr,
        )
        return 2

    combined = result.stdout + result.stderr
    print(combined.strip() or "(no output)")

    # --help should exit with code 0 and mention the program name or "usage"
    if result.returncode != 0:
        print(
            f"[smoke_test] FAIL – process exited with code {result.returncode}.",
            file=sys.stderr,
        )
        return 1

    if not any(kw in combined.lower() for kw in ("usage", "mode", "mirai")):
        print(
            "[smoke_test] WARN – output does not contain expected keywords "
            "('usage', 'mode', 'mirai').  Check output above.",
            file=sys.stderr,
        )
        # Not a hard failure – the app may still be working correctly.

    print("[smoke_test] PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="MirAI_OS smoke test")
    parser.add_argument(
        "--exe",
        metavar="PATH",
        default=None,
        help="Path to the built MirAI_OS executable. "
             "If omitted, tests the Python source entry-point (main.py).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        metavar="SECONDS",
        help="Maximum time to wait for the process (default: 30).",
    )
    args = parser.parse_args()

    if args.exe:
        exe_path = Path(args.exe)
        if not exe_path.exists():
            print(
                f"[smoke_test] ERROR: specified executable not found: {exe_path}",
                file=sys.stderr,
            )
            return 2
        target = [str(exe_path)]
    else:
        # Fall back to running main.py directly with the current interpreter.
        repo_root = Path(__file__).parent.resolve()
        main_py = repo_root / "main.py"
        if not main_py.exists():
            print(
                f"[smoke_test] ERROR: main.py not found at {main_py}",
                file=sys.stderr,
            )
            return 2
        target = [sys.executable, str(main_py)]

    return run_smoke_test(target, timeout=args.timeout)


if __name__ == "__main__":
    sys.exit(main())
