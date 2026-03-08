"""
MirAI_OS — Main Entry Point

Usage:
  python main.py              # Launch Lab web UI (default)
  python main.py bot          # Start Telegram bot
  python main.py lab          # Start Lab UI
  python main.py chat         # Interactive CLI chat
  python main.py agent <task> # Run autonomous agent on a task
"""
from __future__ import annotations

import asyncio
import sys

from config.settings import settings


def _apply_optimizations() -> None:
    """Apply Legion Go hardware optimizations at startup."""
    if settings.legion_go_enabled:
        from system.legion_go_optimizer import LegionGoOptimizer
        LegionGoOptimizer.apply()


def run_lab() -> None:
    from lab.lab_interface import Lab
    lab = Lab()
    lab.launch()


def run_bot() -> None:
    from bot.telegram_bot import MirAIBot
    bot = MirAIBot()
    bot.run()


async def run_chat() -> None:
    """Interactive CLI chat loop."""
    from core.llm_engine import LLMEngine
    from core.context_optimizer import optimizer

    try:
        from rich.console import Console
        console = Console()
    except ImportError:
        console = None

    history: list[dict] = []

    if console:
        console.print("[bold magenta]MirAI_OS[/bold magenta] — CLI Chat (type 'exit' to quit)")
        console.print(optimizer.summary())
    else:
        print("MirAI_OS — CLI Chat (type 'exit' to quit)")

    async with LLMEngine() as engine:
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nEl Psy Kongroo. Goodbye!")
                break
            if user_input.lower() in ("exit", "quit"):
                print("El Psy Kongroo. Goodbye!")
                break
            if not user_input:
                continue
            reply = await engine.chat(user_input, history=history)
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": reply})
            print(f"\nMirAI: {reply}")


async def run_agent(task: str) -> None:
    from core.agent_flow import AgentFlow
    from core.context_optimizer import optimizer

    print(optimizer.summary())
    print(f"\nRunning agent on task: {task}\n")
    agent = AgentFlow()
    result = await agent.run(task)
    print(f"\nResult:\n{result}")


def main() -> None:
    _apply_optimizations()

    args = sys.argv[1:]
    command = args[0] if args else "lab"

    if command == "lab":
        run_lab()
    elif command == "bot":
        run_bot()
    elif command == "chat":
        asyncio.run(run_chat())
    elif command == "agent":
        task = " ".join(args[1:]) if len(args) > 1 else "Describe MirAI_OS capabilities"
        asyncio.run(run_agent(task))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
