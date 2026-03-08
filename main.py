#!/usr/bin/env python3
"""
main.py
───────
MirAI_OS  –  Entry Point
═════════════════════════════════════════════════════════════════════════════
Run modes
─────────────────────
  python main.py          → interactive CLI session
  python main.py telegram → start Telegram bot
  python main.py --help   → show help

This file is also the target for PyInstaller when building a Windows .exe.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent))

import typer
from loguru import logger
from rich.console import Console

from mirai.settings import settings

app = typer.Typer(
    name="mirai",
    help="MirAI_OS – Autonomous AI Agent for Kali Linux / WSL2",
    add_completion=False,
)
console = Console()


def _configure_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
    )
    log_file = settings.data_dir / "mirai.log"
    logger.add(log_file, level="DEBUG", rotation="10 MB", retention="7 days")


@app.command("cli")
def cmd_cli(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview self-mods without committing"),
) -> None:
    """Start an interactive CLI session with MirAI."""
    _configure_logging()
    from mirai.agent import Agent

    agent = Agent(dry_run=dry_run)
    try:
        agent.run_cli()
    finally:
        agent.shutdown()


@app.command("telegram")
def cmd_telegram(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview self-mods without committing"),
) -> None:
    """Start the Telegram bot interface."""
    _configure_logging()
    from mirai.agent import Agent

    agent = Agent(dry_run=dry_run)
    try:
        agent.run_telegram()
    finally:
        agent.shutdown()


@app.command("selfmod")
def cmd_selfmod(
    instruction: str = typer.Argument(..., help="Natural-language modification instruction"),
    path: str = typer.Option("", "--path", "-p", help="Specific file to modify"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Preview without committing"),
) -> None:
    """Apply a self-modification to the codebase."""
    _configure_logging()
    from mirai.agent import Agent

    agent = Agent(dry_run=dry_run)
    if path:
        result = agent.self_mod.modify_file(path, instruction)
    else:
        result = agent.self_mod.add_feature(instruction)
    console.print(result)
    agent.shutdown()


@app.command("review")
def cmd_review() -> None:
    """Ask MirAI to review its own codebase and suggest improvements."""
    _configure_logging()
    from mirai.agent import Agent

    agent = Agent(dry_run=True)
    result = agent.self_mod.review_self()
    from rich.markdown import Markdown

    console.print(Markdown(result))
    agent.shutdown()


@app.command("anon")
def cmd_anon() -> None:
    """Show the current exit IP and rotate the Tor identity."""
    _configure_logging()
    from mirai.anonymity import get_current_ip, rotate_identity

    console.print(f"Current exit IP: {get_current_ip()}")
    ok = rotate_identity()
    if ok:
        console.print(f"New exit IP:     {get_current_ip()}")
    else:
        console.print("[yellow]Rotation failed (is Tor running?).[/yellow]")


# Default command: CLI session
@app.callback(invoke_without_command=True)
def default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        cmd_cli()


if __name__ == "__main__":
    app()
