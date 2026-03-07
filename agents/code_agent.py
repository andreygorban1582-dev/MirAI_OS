"""
MirAI OS — Code Execution Agent
Runs Python, Bash, and other code in a subprocess sandbox.
Full access to WSL/Kali environment.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from agents.base_agent import AgentTask, AgentResult, BaseAgent, Tool, ToolResult

logger = logging.getLogger("mirai.agent.code")

MAX_OUTPUT_BYTES = 1024 * 1024  # 1MB


class CodeAgent(BaseAgent):
    name = "code_agent"
    description = "Executes Python scripts, Bash commands, and shell operations in WSL/Kali environment"

    def _register_tools(self) -> None:
        self.register_tool(Tool("run_python", "Execute a Python script string", self._run_python))
        self.register_tool(Tool("run_bash", "Execute a Bash command or script", self._run_bash))
        self.register_tool(Tool("run_command", "Run any shell command", self._run_command))
        self.register_tool(Tool("install_package", "Install a Python or system package", self._install_pkg))
        self.register_tool(Tool("read_file", "Read a file from the filesystem", self._read_file))
        self.register_tool(Tool("write_file", "Write content to a file", self._write_file))
        self.register_tool(Tool("list_dir", "List directory contents", self._list_dir))

    async def execute(self, task: AgentTask) -> AgentResult:
        action = task.params.get("action", "run_bash")
        code = task.params.get("code", task.description)
        result = await self.run_tool(action, code=code, **task.params)
        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            success=result.success,
            output=result.output,
            error=result.error,
            duration_ms=result.duration_ms,
        )

    async def _run_subprocess(self, cmd: list[str], input_data: str | None = None, timeout: int = 120) -> ToolResult:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if input_data else asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(input_data.encode() if input_data else None),
                timeout=timeout,
            )
            output = stdout[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
            success = proc.returncode == 0
            return ToolResult(success=success, output=output, data=proc.returncode)
        except asyncio.TimeoutError:
            return ToolResult(success=False, output="", error=f"Timeout after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _run_python(self, code: str, **_) -> ToolResult:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            fname = f.name
        try:
            return await self._run_subprocess(["python3", fname])
        finally:
            Path(fname).unlink(missing_ok=True)

    async def _run_bash(self, code: str, **_) -> ToolResult:
        with tempfile.NamedTemporaryFile(suffix=".sh", mode="w", delete=False) as f:
            f.write("#!/bin/bash\nset -euo pipefail\n" + code)
            fname = f.name
        os.chmod(fname, 0o700)
        try:
            return await self._run_subprocess(["bash", fname])
        finally:
            Path(fname).unlink(missing_ok=True)

    async def _run_command(self, code: str, **_) -> ToolResult:
        return await self._run_subprocess(["bash", "-c", code])

    async def _install_pkg(self, code: str, **_) -> ToolResult:
        pkg = code.strip()
        if pkg.startswith("apt") or pkg.startswith("pip"):
            return await self._run_bash(pkg)
        # Try pip first, then apt
        result = await self._run_subprocess(["pip3", "install", pkg])
        if not result.success:
            result = await self._run_subprocess(["sudo", "apt-get", "install", "-y", pkg])
        return result

    async def _read_file(self, code: str, **_) -> ToolResult:
        path = Path(code.strip())
        try:
            content = path.read_text(errors="replace")
            return ToolResult(success=True, output=content[:50000])
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _write_file(self, code: str, path: str = "", content: str = "", **_) -> ToolResult:
        target = Path(path or code.strip())
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            return ToolResult(success=True, output=f"Written to {target}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _list_dir(self, code: str, **_) -> ToolResult:
        path = Path(code.strip() or ".")
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
            lines = [
                f"{'[DIR] ' if e.is_dir() else '[FILE]'} {e.name}"
                for e in entries[:200]
            ]
            return ToolResult(success=True, output="\n".join(lines))
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
