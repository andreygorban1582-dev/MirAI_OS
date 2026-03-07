"""
MirAI OS — Base Agent
All agents inherit from here. Provides tool registration,
execution lifecycle, and result formatting.
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("mirai.agent")


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class ToolResult:
    success: bool
    output: str
    data: Any = None
    error: Optional[str] = None
    duration_ms: int = 0


@dataclass
class AgentTask:
    task_id: str
    description: str
    params: dict = field(default_factory=dict)
    session_id: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class AgentResult:
    task_id: str
    agent_name: str
    success: bool
    output: str
    data: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    sub_results: list["AgentResult"] = field(default_factory=list)


class Tool:
    """A callable tool with metadata."""

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        requires_confirmation: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.func = func
        self.requires_confirmation = requires_confirmation

    async def execute(self, **kwargs) -> ToolResult:
        start = time.monotonic()
        try:
            if asyncio.iscoroutinefunction(self.func):
                result = await self.func(**kwargs)
            else:
                result = await asyncio.to_thread(self.func, **kwargs)
            elapsed = int((time.monotonic() - start) * 1000)
            if isinstance(result, ToolResult):
                result.duration_ms = elapsed
                return result
            return ToolResult(success=True, output=str(result), duration_ms=elapsed)
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            logger.error(f"Tool {self.name} error: {e}")
            return ToolResult(success=False, output="", error=str(e), duration_ms=elapsed)


class BaseAgent(ABC):
    """Abstract base for all MirAI agents."""

    name: str = "base"
    description: str = "Base agent"

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self.status = AgentStatus.IDLE
        self._register_tools()

    @abstractmethod
    def _register_tools(self) -> None:
        """Register tools specific to this agent."""

    def register_tool(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute the given task."""

    async def run_tool(self, tool_name: str, **kwargs) -> ToolResult:
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(success=False, output="", error=f"Tool '{tool_name}' not found")
        return await tool.execute(**kwargs)

    def schema_for_llm(self) -> dict:
        """Return this agent as a tool schema for LLM function-calling."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        t.name: {"type": "string", "description": t.description}
                        for t in self._tools.values()
                    },
                },
            },
        }
