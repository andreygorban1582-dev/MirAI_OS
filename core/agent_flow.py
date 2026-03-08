"""
Autonomous Agent Flow — MirAI_OS

Implements a ReAct-style (Reason + Act) agent loop that can use tools
(web search, code execution, file I/O, Kali integration, etc.) to
complete multi-step tasks autonomously.
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

from core.llm_engine import LLMEngine
from core.context_optimizer import optimizer


# ------------------------------------------------------------------
# Tool definition
# ------------------------------------------------------------------

@dataclass
class Tool:
    name: str
    description: str
    func: Callable[..., Coroutine[Any, Any, str]]
    parameters: dict = field(default_factory=dict)

    async def call(self, **kwargs: Any) -> str:
        return await self.func(**kwargs)

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


# ------------------------------------------------------------------
# Built-in tools
# ------------------------------------------------------------------

async def _tool_think(thought: str) -> str:
    """Internal reasoning step (no-op externally)."""
    return f"[Thought] {thought}"


async def _tool_finish(answer: str) -> str:
    return f"FINAL_ANSWER: {answer}"


async def _tool_python(code: str) -> str:
    """Execute Python code in a restricted local namespace."""
    import io  # noqa: PLC0415
    import contextlib  # noqa: PLC0415
    namespace: dict = {}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(code, "<agent>", "exec"), namespace)  # noqa: S102
        output = buf.getvalue()
        result = namespace.get("result", "")
        return f"Output:\n{output}\nResult: {result}"
    except Exception as exc:
        return f"Error: {exc}"


async def _tool_read_file(path: str) -> str:
    try:
        with open(path) as f:
            return f.read(4096)
    except OSError as exc:
        return f"Error reading file: {exc}"


async def _tool_write_file(path: str, content: str) -> str:
    try:
        with open(path, "w") as f:
            f.write(content)
        return f"Wrote {len(content)} bytes to {path}"
    except OSError as exc:
        return f"Error writing file: {exc}"


DEFAULT_TOOLS: list[Tool] = [
    Tool(
        name="think",
        description="Reason about the problem before acting.",
        func=_tool_think,
        parameters={"thought": {"type": "string", "description": "Your reasoning"}},
    ),
    Tool(
        name="python",
        description="Execute Python code and return the output.",
        func=_tool_python,
        parameters={"code": {"type": "string", "description": "Python code to execute"}},
    ),
    Tool(
        name="read_file",
        description="Read the content of a file.",
        func=_tool_read_file,
        parameters={"path": {"type": "string", "description": "File path"}},
    ),
    Tool(
        name="write_file",
        description="Write content to a file.",
        func=_tool_write_file,
        parameters={
            "path": {"type": "string", "description": "File path"},
            "content": {"type": "string", "description": "Content to write"},
        },
    ),
    Tool(
        name="finish",
        description="Provide the final answer and stop the agent loop.",
        func=_tool_finish,
        parameters={"answer": {"type": "string", "description": "Final answer"}},
    ),
]


# ------------------------------------------------------------------
# Agent
# ------------------------------------------------------------------

_REACT_SYSTEM = """You are an autonomous AI agent running on MirAI_OS.
You solve tasks step-by-step using available tools.

Available tools:
{tools}

Respond ONLY with a JSON object in one of these formats:
  {{"tool": "think", "thought": "..."}}
  {{"tool": "python", "code": "..."}}
  {{"tool": "read_file", "path": "..."}}
  {{"tool": "write_file", "path": "...", "content": "..."}}
  {{"tool": "finish", "answer": "..."}}

Do NOT include any explanation outside the JSON object.
"""


class AgentFlow:
    """ReAct-style autonomous agent."""

    def __init__(
        self,
        tools: list[Tool] | None = None,
        max_steps: int = 10,
        model: Optional[str] = None,
    ) -> None:
        self.tools: dict[str, Tool] = {t.name: t for t in (tools or DEFAULT_TOOLS)}
        self.max_steps = max_steps
        self.model = model
        self._history: list[dict] = []

    def _system_prompt(self) -> str:
        tool_descriptions = "\n".join(
            f"- {t.name}: {t.description}" for t in self.tools.values()
        )
        return _REACT_SYSTEM.format(tools=tool_descriptions)

    async def run(self, task: str) -> str:
        """Run the agent on a task and return the final answer."""
        budget = optimizer.get_budget()
        engine = LLMEngine(
            model=self.model,
            system_prompt=self._system_prompt(),
            max_tokens=min(512, budget.max_tokens // 4),
        )
        self._history = []

        async with engine:
            for step in range(self.max_steps):
                prompt = task if step == 0 else "Continue with the next step."
                response = await engine.chat(prompt, history=self._history)
                self._history.append({"role": "user", "content": prompt})
                self._history.append({"role": "assistant", "content": response})

                # Parse tool call
                action = self._parse_action(response)
                if action is None:
                    continue

                tool_name = action.pop("tool", None)
                if tool_name not in self.tools:
                    continue

                observation = await self.tools[tool_name].call(**action)

                if observation.startswith("FINAL_ANSWER:"):
                    return observation.removeprefix("FINAL_ANSWER:").strip()

                # Feed observation back as user context
                self._history.append({
                    "role": "user",
                    "content": f"Observation: {observation}",
                })

        return "Agent reached maximum steps without a final answer."

    @staticmethod
    def _parse_action(text: str) -> dict | None:
        """Extract the first JSON object from the LLM response."""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None
