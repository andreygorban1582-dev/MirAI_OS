"""
smoke_test.py – Quick sanity checks for MirAI_OS
Exit codes: 0 = all passed, 1 = failure
"""

import subprocess
import sys
import os
import importlib.util


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    detail_str = f" ({detail})" if detail else ""
    print(f"  [{status}] {name}{detail_str}")
    return ok


def main() -> int:
    print("\nMirAI_OS Smoke Tests")
    print("=" * 40)
    results = []

    # 1. main.py exists
    main_py = os.path.join(os.path.dirname(__file__), "main.py")
    results.append(check("main.py exists", os.path.isfile(main_py)))

    # 2. main.py --help works
    try:
        proc = subprocess.run(
            [sys.executable, main_py, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        ok = proc.returncode == 0 and ("mirai" in proc.stdout.lower() or "mode" in proc.stdout.lower())
        results.append(check("main.py --help", ok, proc.stdout[:80].strip()))
    except Exception as exc:
        results.append(check("main.py --help", False, str(exc)))

    # 3. docker-compose.yml exists and mentions ollama
    compose_path = os.path.join(os.path.dirname(__file__), "docker-compose.yml")
    if os.path.isfile(compose_path):
        with open(compose_path) as f:
            content = f.read()
        results.append(check("docker-compose.yml has ollama service", "ollama" in content))
        results.append(check("docker-compose.yml has orchestrator service", "orchestrator" in content))
        results.append(check("docker-compose.yml has postgres service", "postgres" in content))
        results.append(check("docker-compose.yml has redis service", "redis" in content))
    else:
        results.append(check("docker-compose.yml exists", False))

    # 4. install.sh exists
    install_sh = os.path.join(os.path.dirname(__file__), "install.sh")
    results.append(check("install.sh exists", os.path.isfile(install_sh)))

    # 5. .env.example exists
    env_ex = os.path.join(os.path.dirname(__file__), ".env.example")
    results.append(check(".env.example exists", os.path.isfile(env_ex)))

    # 6. containers/orchestrator/orchestrator.py exists
    orch = os.path.join(
        os.path.dirname(__file__), "containers", "orchestrator", "orchestrator.py"
    )
    results.append(check("containers/orchestrator/orchestrator.py exists", os.path.isfile(orch)))

    # 7. orchestrator imports successfully
    if os.path.isfile(orch):
        spec = importlib.util.spec_from_file_location("orchestrator", orch)
        # We can't actually import (missing deps in smoke test env) – just check syntax
        try:
            with open(orch) as f:
                src = f.read()
            compile(src, orch, "exec")
            results.append(check("orchestrator.py syntax valid", True))
        except SyntaxError as exc:
            results.append(check("orchestrator.py syntax valid", False, str(exc)))

    # 8. main.py syntax check
    with open(main_py) as f:
        src = f.read()
    try:
        compile(src, main_py, "exec")
        results.append(check("main.py syntax valid", True))
    except SyntaxError as exc:
        results.append(check("main.py syntax valid", False, str(exc)))

    # ── Summary ──────────────────────────────────────────────
    print("=" * 40)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("All smoke tests passed!")
        return 0
    else:
        print(f"{total - passed} test(s) FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
