"""
Core Orchestrator — wires the LLM together with the codespace tools so the AI
can autonomously read, modify, and execute code within the repository.

Quick-start::

    import asyncio
    from src.core_orchestrator import Orchestrator

    async def main():
        orch = Orchestrator()
        reply = await orch.run("Show me the project structure.")
        print(reply)

    asyncio.run(main())
"""

from __future__ import annotations

import json
import os
from typing import Optional

from openai import AsyncOpenAI

from src.llm.tools import TOOLS, dispatch_tool_call

_SYSTEM_PROMPT = """\
You are MirAI, an autonomous AI operating system assistant with full access to
the repository's codespace.  You can read, write, create, and delete files, \
list directories, search code, and execute shell commands — all scoped to the
workspace root.

When you need information about the codebase, always prefer using your tools
(read_file, list_directory, get_project_structure, search_code) over making
assumptions.  When asked to make a change, use write_file or create_file, and
confirm the result with read_file afterwards.
"""


class Orchestrator:
    """
    Minimal agentic loop:  send a user message → model decides which tools
    to call → tools are executed → results fed back → loop until the model
    returns a plain text reply.
    """

    def __init__(
        self,
        model: str = "openai/gpt-4o",
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        max_tool_rounds: int = 20,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key or os.environ["OPENROUTER_API_KEY"],
            base_url=base_url,
        )
        self._model = model
        self._max_tool_rounds = max_tool_rounds

    async def run(self, user_message: str) -> str:
        """Send *user_message* and return the final assistant reply."""
        messages: list[dict] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        for _ in range(self._max_tool_rounds):
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            choice = response.choices[0]
            messages.append(
                {
                    "role": "assistant",
                    "content": choice.message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in (choice.message.tool_calls or [])
                    ] or None,
                }
            )

            if choice.finish_reason != "tool_calls":
                return choice.message.content or ""

            for tool_call in choice.message.tool_calls:
                result = dispatch_tool_call(
                    tool_call.function.name,
                    tool_call.function.arguments,
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        return "Maximum tool-call rounds reached without a final answer."
