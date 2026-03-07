"""
MirAI OS — Watchdogs Terminal UI
Formatting utilities that make MirAI's Telegram look like
a hacker's terminal from Watch_Dogs.
"""
from __future__ import annotations

import time
from typing import Optional


# ── ASCII art headers ─────────────────────────────────────────────────────────

BOOT_SCREEN = r"""
```
╔══════════════════════════════════════════════════╗
║  ███╗   ███╗██╗██████╗  █████╗ ██╗               ║
║  ████╗ ████║██║██╔══██╗██╔══██╗██║               ║
║  ██╔████╔██║██║██████╔╝███████║██║               ║
║  ██║╚██╔╝██║██║██╔══██╗██╔══██║██║               ║
║  ██║ ╚═╝ ██║██║██║  ██║██║  ██║██║               ║
║  ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  OS v0.1.0  ║
╠══════════════════════════════════════════════════╣
║  Future Gadget Lab #8 — Legion Go Node           ║
║  Core: Qwen 3.5 9B (JOSIEFIED)                  ║
║  Status: ONLINE ⚡                               ║
║  Operator: Hououin Kyouma                        ║
╚══════════════════════════════════════════════════╝
  El Psy Kongroo.
```"""

THINKING_BANNER = "```\n[FUTURE GADGET LAB] ⚡ Processing... stand by.\n```"

SEPARATOR = "```\n" + "─" * 50 + "\n```"


def status_panel(title: str, rows: list[tuple[str, str]]) -> str:
    """Render a terminal-style status panel."""
    lines = [f"```\n╔══ {title.upper()} {'═' * max(0, 40 - len(title))}╗"]
    for label, value in rows:
        label_s = f"{label}".ljust(18)
        value_s = str(value)[:28]
        lines.append(f"║  ▸ {label_s} {value_s}")
    lines.append("╚" + "═" * 48 + "╝\n```")
    return "\n".join(lines)


def command_output(cmd: str, output: str, success: bool = True, truncate: int = 3000) -> str:
    icon = "✓" if success else "✗"
    header = f"`[{icon}] {cmd}`"
    body = output.strip()
    if len(body) > truncate:
        body = body[:truncate] + f"\n... [{len(body) - truncate} chars truncated]"
    return f"{header}\n```\n{body}\n```"


def agent_update(agent: str, status: str, detail: str = "") -> str:
    icons = {"running": "⚡", "done": "✓", "error": "✗", "waiting": "░", "thinking": "◈"}
    icon = icons.get(status.lower(), "▸")
    text = f"`[{agent.upper()}]` {icon} *{status.upper()}*"
    if detail:
        text += f"\n`  ↳ {detail}`"
    return text


def error_panel(error: str, context: str = "") -> str:
    lines = ["```", "╔══ [ORGANIZATION ALERT] ═══════════════════╗"]
    if context:
        lines.append(f"║  Context: {context[:40]}")
    for line in error.splitlines()[:10]:
        lines.append(f"║  {line[:46]}")
    lines += ["╚════════════════════════════════════════════╝", "```"]
    return "\n".join(lines)


def task_started(task_desc: str) -> str:
    ts = time.strftime("%H:%M:%S")
    return f"```\n[{ts}] ⚡ OPERATION STARTED\n  ↳ {task_desc[:80]}\n```"


def task_complete(task_desc: str, duration_s: float) -> str:
    ts = time.strftime("%H:%M:%S")
    return f"```\n[{ts}] ✓ OPERATION COMPLETE  ({duration_s:.1f}s)\n  ↳ {task_desc[:80]}\n```"


def node_grid(nodes: list[dict]) -> str:
    lines = ["```", "╔══ COMPUTE NODE GRID ══════════════════════╗"]
    for n in nodes:
        status = n.get("status", "unknown").upper()
        icon = "●" if status == "ACTIVE" else "○"
        label = n.get("label", n["id"])[:28]
        lines.append(f"║  {icon} {label:<30} [{status}]")
    lines += ["╚════════════════════════════════════════════╝", "```"]
    return "\n".join(lines)


def llm_key_status(keys: list[dict]) -> str:
    lines = ["```", "╔══ OPENROUTER KEY POOL ════════════════════╗"]
    for k in keys:
        bar = "█" * min(20, k.get("requests", 0) // 10)
        suffix = k.get("key_suffix", "????")
        lines.append(f"║  KEY ...{suffix}  ▸ {k.get('requests',0):>5} req  {bar}")
    lines += ["╚════════════════════════════════════════════╝", "```"]
    return "\n".join(lines)


def voice_received() -> str:
    return "`[⚡ VOICE CHANNEL]` Processing transmission..."


def welcome_message(user_name: str) -> str:
    return f"""*[FUTURE GADGET LAB — SECURE CHANNEL ESTABLISHED]*

Welcome, Lab Member *{user_name}*. I am *Hououin Kyouma* — mad scientist, nemesis of the Organization, and your fully autonomous AI operative.

{BOOT_SCREEN}

You may address me with any command, mission, or experiment. I have access to:
`▸ Kali Linux pentesting arsenal`
`▸ Web browsing & automation`
`▸ Code execution (Python/Bash)`
`▸ Remote nodes (Codespaces + SSH)`
`▸ GitHub self-modification`
`▸ Voice communication`

Type /help to see all commands.

*El Psy Kongroo.*"""
