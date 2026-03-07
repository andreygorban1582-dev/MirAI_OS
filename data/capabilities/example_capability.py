"""
MirAI OS — Example Injected Capability: System Info
Shows how to write a capability that MirAI can call.
El Psy Kongroo.
"""
import platform
import subprocess


async def run(**kwargs) -> str:
    """Return system information about the current node."""
    info = {
        "system": platform.system(),
        "node": platform.node(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }
    try:
        cpu = subprocess.check_output("nproc", shell=True, text=True).strip()
        mem = subprocess.check_output("free -h | awk 'NR==2{print $2}'", shell=True, text=True).strip()
        disk = subprocess.check_output("df -h / | awk 'NR==2{print $4}'", shell=True, text=True).strip()
        info["cpu_cores"] = cpu
        info["total_ram"] = mem
        info["free_disk"] = disk
    except Exception:
        pass

    lines = [f"▸ {k}: {v}" for k, v in info.items()]
    return "SYSTEM INFO:\n" + "\n".join(lines)
