"""
MirAI_OS  –  Docker control mod (Mod 2)
Lets MirAI inspect and control Docker containers via chat commands.
Commands:
    !containers       – list running containers
    !logs <name>      – tail last 20 lines of container logs
    !restart <name>   – restart a container
"""

import subprocess
import shlex

MOD_NAME    = "docker_control"
MOD_VERSION = "2.0.0"


def on_startup(ctx):
    print(f"[{MOD_NAME}] Docker control mod loaded")


def on_message(message: str, ctx: dict):
    msg = message.strip()
    if not msg.startswith("!"):
        return None

    parts = shlex.split(msg)
    cmd   = parts[0].lower()

    if cmd == "!containers":
        return _run_docker(["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"])

    if cmd == "!logs" and len(parts) >= 2:
        name = parts[1]
        return _run_docker(["docker", "logs", "--tail", "20", name])

    if cmd == "!restart" and len(parts) >= 2:
        name = parts[1]
        out = _run_docker(["docker", "restart", name])
        return f"Restarted {name}: {out}"

    return None


def _run_docker(args: list) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        output = result.stdout or result.stderr
        return output.strip()[:2000] or "(no output)"
    except Exception as exc:
        return f"[docker_control error] {exc}"
