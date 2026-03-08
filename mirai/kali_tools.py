"""
mirai/kali_tools.py
───────────────────
Kali Linux Integration – Shell Command Execution
═════════════════════════════════════════════════════════════════════════════
What this module does
─────────────────────
• Exposes a safe interface for executing approved shell commands on the host
  Kali Linux system (running inside WSL2 on the Legion Go).
• Maintains a whitelist of allowed tool names (from config.yaml) so MirAI
  cannot be tricked into running arbitrary dangerous commands.
• Creates and cleans up a dedicated workspace directory for tool output.
• Captures stdout, stderr, and the return code from every command.
• Streams long-running output to the caller via a generator.

Security model
──────────────
• Only executables listed in kali.allowed_tools may be invoked as the first
  token of any command.
• Commands are run with a configurable timeout (default 60 s).
• Working directory is always set to kali.workspace (never / or ~).
• Shell expansion is intentionally DISABLED (shell=False) to prevent injection.

Example allowed commands
────────────────────────
  nmap -sV 192.168.1.1
  python3 -c "print('hello')"
  git status
  curl https://example.com
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Generator

from loguru import logger

from mirai.settings import settings


class KaliTools:
    """
    Safe wrapper for running Kali Linux CLI tools.

    Parameters
    ----------
    workspace : str, optional
        Override the workspace directory from settings.
    allowed_tools : list[str], optional
        Override the allowed tools list from settings.
    timeout : int
        Maximum seconds a command may run before being killed.
    """

    def __init__(
        self,
        workspace: str | None = None,
        allowed_tools: list[str] | None = None,
        timeout: int = 60,
    ) -> None:
        self._workspace = Path(workspace or settings.kali_workspace)
        self._allowed_tools = set(allowed_tools or settings.kali_allowed_tools)
        self._timeout = timeout
        self._workspace.mkdir(parents=True, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(self, command: str) -> dict:
        """
        Execute `command` and return a result dict.

        Parameters
        ----------
        command : str
            Shell command string (will be split safely via shlex).

        Returns
        -------
        dict with keys:
            stdout  – captured standard output
            stderr  – captured standard error
            rc      – return code (0 = success)
            command – the original command string
            allowed – bool (False if the command was blocked)
        """
        if not settings.allow_shell_exec:
            return self._blocked(command, "Shell execution is disabled in settings.")

        args = shlex.split(command)
        if not args:
            return self._blocked(command, "Empty command.")

        # Resolve the tool to its absolute path and verify it is in the allowed list
        tool_name = os.path.basename(args[0])
        if tool_name not in self._allowed_tools:
            return self._blocked(
                command,
                f"Tool '{tool_name}' is not in the allowed list: {sorted(self._allowed_tools)}",
            )
        resolved = shutil.which(tool_name)
        if resolved is None:
            return self._blocked(command, f"Tool '{tool_name}' not found on PATH.")
        # Replace the user-supplied first token with the fully-resolved path
        args[0] = resolved

        logger.info(f"Running: {command}")
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=str(self._workspace),
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "rc": result.returncode,
                "command": command,
                "allowed": True,
            }
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out after {self._timeout}s: {command}")
            return {
                "stdout": "",
                "stderr": f"Timed out after {self._timeout}s",
                "rc": -1,
                "command": command,
                "allowed": True,
            }
        except FileNotFoundError:
            return {
                "stdout": "",
                "stderr": f"Executable not found: {args[0]}",
                "rc": -1,
                "command": command,
                "allowed": True,
            }

    def stream(self, command: str) -> Generator[str, None, None]:
        """
        Execute `command` and yield output lines as they arrive.

        Useful for long-running commands (e.g. nmap scans) where you want
        real-time feedback.
        """
        args = shlex.split(command)
        if not args:
            yield "[Error] Empty command."
            return

        tool_name = os.path.basename(args[0])
        if tool_name not in self._allowed_tools:
            yield f"[Blocked] '{tool_name}' is not allowed."
            return
        resolved = shutil.which(tool_name)
        if resolved is None:
            yield f"[Error] '{tool_name}' not found on PATH."
            return
        args[0] = resolved

        try:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self._workspace),
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                yield line.rstrip()
            proc.wait()
        except FileNotFoundError:
            yield f"[Error] Executable not found: {args[0]}"

    def list_workspace(self) -> list[str]:
        """Return all files currently in the workspace directory."""
        return [str(p) for p in self._workspace.iterdir() if p.is_file()]

    def clean_workspace(self) -> None:
        """Delete all files in the workspace (does not remove the directory)."""
        for p in self._workspace.iterdir():
            if p.is_file():
                p.unlink()
        logger.info(f"Workspace cleaned: {self._workspace}")

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _blocked(command: str, reason: str) -> dict:
        logger.warning(f"Command blocked – {reason}: {command}")
        return {
            "stdout": "",
            "stderr": f"[Blocked] {reason}",
            "rc": -1,
            "command": command,
            "allowed": False,
        }
