"""
mirai/agent.py
──────────────
Core AI Agent – The Brain of MirAI_OS
═════════════════════════════════════════════════════════════════════════════
What this module does
─────────────────────
This is the central orchestrator.  It wires together every sub-system:

  LLMEngine            – generates intelligent replies via OpenRouter
  ConversationMemory   – keeps a rolling window of the conversation
  KaliTools            – runs approved shell commands on the host system
  GitHubClient         – reads/writes the repository (Copilot-like access)
  SelfModificationSystem – applies code changes to MirAI's own files
  VoiceIO              – speaks replies and listens for voice input
  IdentityRotator      – rotates Tor circuit in the background

The main entry point is `agent.chat(user_message)` which:
  1. Appends the user message to memory.
  2. Sends the full conversation to the LLM.
  3. Parses any tool-call directives embedded in the LLM reply.
  4. Executes tool calls (shell, self-mod, GitHub) and appends results.
  5. Returns the final text reply to the caller.

Tool-call protocol
──────────────────
The LLM is instructed to embed tool calls in its reply using a simple syntax:

  !!SHELL!! <command>
  !!SELFMOD!! <path> :: <instruction>
  !!GITHUB_READ!! <path>
  !!GITHUB_WRITE!! <path> :: <content>

The agent scans every line of the LLM reply, executes matching directives,
replaces them with their output, then returns the cleaned reply.
"""

from __future__ import annotations

import re
from typing import Optional

from loguru import logger

from mirai.anonymity import IdentityRotator
from mirai.github_client import GitHubClient
from mirai.kali_tools import KaliTools
from mirai.llm import LLMEngine
from mirai.memory import ConversationMemory
from mirai.self_mod import SelfModificationSystem
from mirai.settings import settings
from mirai.voice import VoiceIO


class Agent:
    """
    The central MirAI agent.

    Instantiate once, then call `.chat()` or `.run_telegram()`.

    Parameters
    ----------
    dry_run : bool
        When True, self-modification proposals are printed but not committed.
    """

    def __init__(self, dry_run: bool = False) -> None:
        logger.info(f"Initialising {settings.agent_name} v{self._version()}…")

        # Core sub-systems
        self.llm = LLMEngine()
        self.memory = ConversationMemory(max_messages=settings.context_window * 2)
        self.kali = KaliTools()
        self.github = GitHubClient()
        self.self_mod = SelfModificationSystem(
            github=self.github, llm=self.llm, dry_run=dry_run
        )
        self.voice = VoiceIO()
        self._rotator = IdentityRotator()

        # Start background Tor rotation
        self._rotator.start()

        logger.info(f"{settings.agent_name} ready.")

    # ── Main chat interface ────────────────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        """
        Process a user message and return the agent's reply.

        This is the primary interface used by both the Telegram bot and the
        CLI.

        Parameters
        ----------
        user_message : str
            Raw text from the user.

        Returns
        -------
        str
            The agent's final reply (after any tool calls have been executed).
        """
        # 1. Store user turn
        self.memory.add("user", user_message)

        # 2. Ask LLM
        raw_reply = self.llm.chat(self.memory.get_messages())

        # 3. Parse & execute embedded tool calls
        processed_reply = self._process_tool_calls(raw_reply)

        # 4. Store assistant turn
        self.memory.add("assistant", processed_reply)

        # 5. Optionally speak the reply
        if self.voice.is_enabled:
            self.voice.speak(processed_reply)

        return processed_reply

    # ── Tool-call parser ───────────────────────────────────────────────────────

    def _process_tool_calls(self, text: str) -> str:
        """
        Scan `text` for !!DIRECTIVE!! markers and execute them in-place.

        Returns the text with directives replaced by their output.
        """
        lines = text.split("\n")
        output_lines = []

        for line in lines:
            # ── Shell execution ────────────────────────────────────────────────
            m = re.match(r"^!!SHELL!!\s+(.+)$", line.strip())
            if m:
                cmd = m.group(1)
                result = self.kali.run(cmd)
                if result["allowed"]:
                    out = result["stdout"] or result["stderr"] or "(no output)"
                    output_lines.append(f"[shell:{cmd}] {out.strip()}")
                else:
                    output_lines.append(f"[shell BLOCKED] {result['stderr']}")
                continue

            # ── Self-modification ──────────────────────────────────────────────
            m = re.match(r"^!!SELFMOD!!\s+(.+?)\s*::\s*(.+)$", line.strip())
            if m:
                path, instruction = m.group(1), m.group(2)
                result_str = self.self_mod.modify_file(path, instruction)
                output_lines.append(result_str)
                continue

            # ── GitHub read ────────────────────────────────────────────────────
            m = re.match(r"^!!GITHUB_READ!!\s+(.+)$", line.strip())
            if m:
                path = m.group(1).strip()
                content = self.github.read_file(path)
                if content is not None:
                    output_lines.append(f"[github:{path}]\n{content[:800]}")
                else:
                    output_lines.append(f"[github:{path}] File not found or access denied.")
                continue

            # ── GitHub write ───────────────────────────────────────────────────
            m = re.match(r"^!!GITHUB_WRITE!!\s+(.+?)\s*::\s*(.+)$", line.strip(), re.DOTALL)
            if m:
                path, new_content = m.group(1).strip(), m.group(2)
                ok = self.github.write_file(path, new_content)
                output_lines.append(
                    f"[github write {'ok' if ok else 'failed'}] {path}"
                )
                continue

            output_lines.append(line)

        return "\n".join(output_lines)

    # ── Telegram runner ────────────────────────────────────────────────────────

    def run_telegram(self) -> None:
        """Start the Telegram bot (blocking)."""
        from mirai.telegram_bot import TelegramBot
        bot = TelegramBot(agent=self)
        bot.run()

    # ── CLI runner ─────────────────────────────────────────────────────────────

    def run_cli(self) -> None:
        """Interactive terminal session with MirAI."""
        from rich.console import Console
        from rich.markdown import Markdown

        console = Console()
        console.print(f"[bold cyan]{settings.agent_name}[/bold cyan] online. Type 'exit' to quit.\n")

        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[yellow]Goodbye.[/yellow]")
                break

            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[yellow]Goodbye.[/yellow]")
                break

            if not user_input:
                continue

            reply = self.chat(user_input)
            console.print(f"\n[bold green]{settings.agent_name}:[/bold green]")
            console.print(Markdown(reply))
            console.print()

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Clean up resources."""
        self._rotator.stop()
        self.memory.save()
        logger.info(f"{settings.agent_name} shut down.")

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _version() -> str:
        from mirai import __version__
        return __version__
