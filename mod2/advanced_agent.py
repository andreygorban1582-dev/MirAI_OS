"""
Mod 2 – Advanced Agent
Extends the base AgentFlows with deeper reasoning, persistent memory,
web search, and multi-step planning capabilities.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from modules.llm_engine import LLMEngine
    from mod2.memory_system import MemorySystem
    from mod2.web_scraper import WebScraper

import config

logger = logging.getLogger(__name__)

ADVANCED_SYSTEM = (
    f"{config.OKABE_SYSTEM_PROMPT}\n\n"
    "MOD 2 ACTIVE: You now have access to persistent memory, web search, "
    "and advanced multi-step planning. You can recall past interactions, "
    "search the internet, and execute complex multi-step tasks.\n\n"
    "Tool usage format:\n"
    "ACTION: <tool_name>\nINPUT: <tool_input>\n\n"
    "Final answer format:\n"
    "FINAL: <answer>\n\n"
    "Think step by step. Plan before acting."
)


class AdvancedAgent:
    """Mod 2 advanced agent with memory, web search, and planning."""

    def __init__(
        self,
        llm: "LLMEngine",
        memory: Optional["MemorySystem"] = None,
        scraper: Optional["WebScraper"] = None,
    ) -> None:
        self.llm = llm
        self.memory = memory
        self.scraper = scraper
        self._tools: Dict[str, Any] = {}
        self._register_tools()

    # ── tool registration ─────────────────────────────────────────────────────

    def _register_tools(self) -> None:
        self._tools["remember"] = self._tool_remember
        self._tools["recall"] = self._tool_recall
        self._tools["forget"] = self._tool_forget
        self._tools["web_search"] = self._tool_web_search
        self._tools["fetch_page"] = self._tool_fetch_page
        self._tools["think"] = self._tool_think
        self._tools["list_tools"] = self._tool_list_tools

    # ── tools ─────────────────────────────────────────────────────────────────

    def _tool_remember(self, content: str) -> str:
        if self.memory is None:
            return "Memory system not available."
        self.memory.store(content)
        return f"Stored: {content[:80]}…" if len(content) > 80 else f"Stored: {content}"

    def _tool_recall(self, query: str) -> str:
        if self.memory is None:
            return "Memory system not available."
        results = self.memory.search(query)
        if not results:
            return "No relevant memories found."
        return "\n".join(f"- {r}" for r in results)

    def _tool_forget(self, query: str) -> str:
        if self.memory is None:
            return "Memory system not available."
        removed = self.memory.forget(query)
        return f"Removed {removed} memory entries matching '{query}'."

    def _tool_web_search(self, query: str) -> str:
        if self.scraper is None:
            return "Web scraper not available."
        return self.scraper.search(query)

    def _tool_fetch_page(self, url: str) -> str:
        if self.scraper is None:
            return "Web scraper not available."
        return self.scraper.fetch(url)

    def _tool_think(self, thought: str) -> str:
        """Scratchpad tool for chain-of-thought reasoning."""
        logger.debug("Agent thought: %s", thought)
        return f"Thought recorded: {thought}"

    def _tool_list_tools(self, _: str) -> str:
        return "Available tools: " + ", ".join(self._tools)

    # ── agent loop ────────────────────────────────────────────────────────────

    def run(self, task: str, max_steps: int = config.AGENT_MAX_STEPS) -> str:
        """Execute a task with full Mod 2 capabilities."""
        # Inject relevant memories into the prompt
        context = ""
        if self.memory:
            memories = self.memory.search(task)
            if memories:
                context = "Relevant memories:\n" + "\n".join(f"- {m}" for m in memories) + "\n\n"

        prompt = f"{context}Task: {task}\n\nAvailable tools: {', '.join(self._tools)}"
        history: List[Dict[str, str]] = []

        for step in range(max_steps):
            response = self.llm.chat(prompt, system=ADVANCED_SYSTEM, history=history)
            logger.debug("Mod2 step %d: %s", step + 1, response[:120])

            # FINAL answer
            final_match = re.search(r"FINAL:\s*(.+)", response, re.DOTALL)
            if final_match:
                answer = final_match.group(1).strip()
                # Auto-save result to memory
                if self.memory:
                    self.memory.store(f"Task: {task} → Result: {answer[:200]}")
                return answer

            # ACTION
            action_match = re.search(
                r"ACTION:\s*(\w+)\s*\nINPUT:\s*(.+?)(?=\nACTION:|\nFINAL:|$)",
                response,
                re.DOTALL,
            )
            if action_match:
                tool = action_match.group(1).strip()
                inp = action_match.group(2).strip()
                obs = self._call_tool(tool, inp)
                history.append({"role": "assistant", "content": response})
                history.append({"role": "user", "content": f"OBSERVATION: {obs}"})
                prompt = f"OBSERVATION: {obs}"
            else:
                return response

        return "Mod 2 agent reached max steps."

    def _call_tool(self, name: str, inp: str) -> str:
        fn = self._tools.get(name)
        if fn is None:
            return f"Unknown tool '{name}'. Use list_tools to see available tools."
        try:
            return fn(inp)
        except Exception as exc:
            logger.error("Tool '%s' error: %s", name, exc)
            return f"Tool error: {exc}"
