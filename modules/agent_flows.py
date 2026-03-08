"""
Autonomous Agent Flows – multi-step reasoning and tool-use chains.
Implements a ReAct-style agent loop with pluggable tools.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from modules.llm_engine import LLMEngine

import config

logger = logging.getLogger(__name__)

AGENT_SYSTEM = (
    f"{config.OKABE_SYSTEM_PROMPT}\n\n"
    "You are also an autonomous agent. When you need to use a tool, respond "
    "with exactly:\nACTION: <tool_name>\nINPUT: <tool_input>\n\n"
    "When you have a final answer, respond with:\nFINAL: <answer>"
)


class AgentFlows:
    """ReAct-style autonomous agent with pluggable tools."""

    def __init__(self, llm: "LLMEngine") -> None:
        self.llm = llm
        self._tools: Dict[str, Callable[[str], str]] = {}
        self._register_defaults()

    # ── tool registration ─────────────────────────────────────────────────────

    def register_tool(self, name: str, fn: Callable[[str], str]) -> None:
        self._tools[name] = fn

    def _register_defaults(self) -> None:
        self.register_tool("python_eval", self._tool_python_eval)
        self.register_tool("list_tools", self._tool_list_tools)

    def _tool_python_eval(self, code: str) -> str:
        """Safely evaluate simple Python literal expressions via ast.literal_eval."""
        import ast

        try:
            result = ast.literal_eval(code)
            return str(result)
        except (ValueError, SyntaxError):
            # Not a literal – try simple arithmetic with ast.parse
            try:
                tree = ast.parse(code, mode="eval")
                # Only allow simple expressions (numbers, strings, lists, dicts)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Call, ast.Import, ast.Attribute)):
                        return "Error: Only literal expressions are allowed."
                result = eval(  # noqa: S307
                    compile(tree, "<string>", "eval"),
                    {"__builtins__": {}},
                )
                return str(result)
            except Exception as exc:
                return f"Error: {exc}"

    def _tool_list_tools(self, _: str) -> str:
        return "Available tools: " + ", ".join(self._tools)

    # ── agent loop ────────────────────────────────────────────────────────────

    def run(self, task: str, max_steps: int = config.AGENT_MAX_STEPS) -> str:
        """Run the agent loop and return the final answer."""
        history: List[Dict[str, str]] = []
        prompt = f"Task: {task}\n\nTools available: {', '.join(self._tools)}"

        for step in range(max_steps):
            response = self.llm.chat(prompt, system=AGENT_SYSTEM, history=history)
            logger.debug("Agent step %d: %s", step + 1, response)

            # Check for FINAL answer
            final_match = re.search(r"FINAL:\s*(.+)", response, re.DOTALL)
            if final_match:
                return final_match.group(1).strip()

            # Check for ACTION
            action_match = re.search(r"ACTION:\s*(\w+)\s*\nINPUT:\s*(.+)", response, re.DOTALL)
            if action_match:
                tool_name = action_match.group(1).strip()
                tool_input = action_match.group(2).strip()
                observation = self._call_tool(tool_name, tool_input)
                obs_msg = f"OBSERVATION: {observation}"
                history.append({"role": "assistant", "content": response})
                history.append({"role": "user", "content": obs_msg})
                prompt = obs_msg
            else:
                # No structured output – treat as final
                return response

        return "Agent reached max steps without a final answer."

    def _call_tool(self, name: str, inp: str) -> str:
        if name not in self._tools:
            return f"Unknown tool '{name}'. Available: {', '.join(self._tools)}"
        try:
            return self._tools[name](inp)
        except Exception as exc:
            logger.error("Tool '%s' error: %s", name, exc)
            return f"Tool error: {exc}"
