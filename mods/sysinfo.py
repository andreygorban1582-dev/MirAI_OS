"""
MirAI_OS  –  System info mod (Mod 2)
Reports CPU, RAM, disk, and container status.
Commands:
    !sysinfo     – full system summary
    !ram         – RAM / swap usage
    !disk        – disk usage
"""

import platform
import shutil

MOD_NAME    = "sysinfo"
MOD_VERSION = "2.0.0"


def on_startup(ctx):
    print(f"[{MOD_NAME}] loaded")


def on_message(message: str, ctx: dict):
    msg = message.strip().lower()

    if msg == "!sysinfo":
        return _full_info()
    if msg in ("!ram", "!memory"):
        return _ram_info()
    if msg == "!disk":
        return _disk_info()

    return None


def _full_info() -> str:
    lines = [
        f"OS:      {platform.system()} {platform.release()}",
        f"Node:    {platform.node()}",
        f"Arch:    {platform.machine()}",
        f"Python:  {platform.python_version()}",
        "",
        _ram_info(),
        _disk_info(),
    ]
    return "\n".join(lines)


def _ram_info() -> str:
    try:
        import psutil
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
        return (
            f"RAM:  {vm.used >> 30:.1f} GB / {vm.total >> 30:.1f} GB  "
            f"({vm.percent}%)\n"
            f"Swap: {sw.used >> 30:.1f} GB / {sw.total >> 30:.1f} GB  "
            f"({sw.percent}%)"
        )
    except ImportError:
        return "RAM: install psutil for details"


def _disk_info() -> str:
    try:
        import psutil
        parts = psutil.disk_partitions()
        lines = []
        for p in parts[:5]:
            try:
                u = psutil.disk_usage(p.mountpoint)
                lines.append(
                    f"{p.mountpoint}: {u.used >> 30:.1f} GB / "
                    f"{u.total >> 30:.1f} GB ({u.percent}%)"
                )
            except PermissionError:
                pass
        return "Disk:\n" + "\n".join(lines)
    except ImportError:
        total, used, free = shutil.disk_usage("/")
        return (
            f"Disk /: {used >> 30:.1f} GB used / "
            f"{total >> 30:.1f} GB total"
        )
