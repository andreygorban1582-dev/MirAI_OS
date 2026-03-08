"""
MirAI_OS smoke test  –  validates that the application starts and responds.
Usage:
    python smoke_test.py                           # test Python source
    python smoke_test.py --exe dist/MirAI_OS.exe  # test built executable
"""

import argparse
import asyncio
import importlib
import subprocess
import sys
import time
from pathlib import Path


def test_imports() -> bool:
    """Check that core modules can be imported."""
    required = ["httpx", "dotenv", "asyncio", "pathlib"]
    failed = []
    for mod in required:
        try:
            importlib.import_module(mod)
        except ImportError:
            failed.append(mod)
    if failed:
        print(f"[FAIL] Missing modules: {failed}")
        return False
    print("[OK] Core imports")
    return True


def test_mod_loader() -> bool:
    """Check that the mod loader initialises without errors."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from mods import ModLoader
        loader = ModLoader()
        assert len(loader) == 0
        print("[OK] ModLoader init")
        return True
    except Exception as exc:
        print(f"[FAIL] ModLoader: {exc}")
        return False


def test_llm_client() -> bool:
    """Check that LLMClient can be instantiated (no actual API calls)."""
    try:
        from main import LLMClient
        client = LLMClient()
        assert client is not None
        print("[OK] LLMClient init")
        return True
    except Exception as exc:
        print(f"[FAIL] LLMClient: {exc}")
        return False


def test_executable(exe_path: str) -> bool:
    """Spawn the built .exe/binary and check it prints a usage line."""
    exe = Path(exe_path)
    if not exe.exists():
        print(f"[FAIL] Executable not found: {exe}")
        return False
    try:
        result = subprocess.run(
            [str(exe), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if "mode" in result.stdout.lower() or result.returncode == 0:
            print(f"[OK] Executable responds: {exe.name}")
            return True
        print(f"[FAIL] Unexpected output: {result.stdout[:200]}")
        return False
    except Exception as exc:
        print(f"[FAIL] Executable error: {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", default=None, help="Path to built executable")
    args = parser.parse_args()

    results = []

    if args.exe:
        results.append(test_executable(args.exe))
    else:
        results.append(test_imports())
        results.append(test_mod_loader())
        results.append(test_llm_client())

    passed = sum(results)
    total  = len(results)
    print(f"\n{'='*40}")
    print(f"Smoke test: {passed}/{total} passed")

    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
