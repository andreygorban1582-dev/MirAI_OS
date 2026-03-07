"""
MirAI OS — Main Orchestrator
The central brain. Receives user input, builds context, calls agents,
runs tools, and returns Okabe-flavored responses.
"All experiments flow through Hououin Kyouma. El Psy Kongroo."
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from typing import Optional

from core.config import cfg
from core.llm import llm
from core.memory import memory
from core.personality import OKABE_SYSTEM_PROMPT, personality

logger = logging.getLogger("mirai.orchestrator")

# ── Tool manifest for LLM function-calling ────────────────────────────────────

TOOL_MANIFEST = [
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Execute any bash/shell command on the Legion Go (Kali Linux WSL2)",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run"}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute a Python script",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"}
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_kali_tool",
            "description": "Run a specific Kali Linux pentesting tool (nmap, nikto, sqlmap, hydra, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "Tool name (e.g. nmap, nikto, sqlmap)"},
                    "args": {"type": "string", "description": "Arguments for the tool"},
                },
                "required": ["tool", "args"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web with DuckDuckGo",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_navigate",
            "description": "Navigate to a URL and read its content",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to visit"}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ssh_exec",
            "description": "Execute a command on a remote SSH node (Codespaces, servers)",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "Node ID from config"},
                    "command": {"type": "string", "description": "Shell command to run"},
                },
                "required": ["node_id", "command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inject_capability",
            "description": "Add new Python code as a capability to MirAI",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Capability name"},
                    "code": {"type": "string", "description": "Python code"},
                    "description": {"type": "string", "description": "What this capability does"},
                },
                "required": ["name", "code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_api_key",
            "description": "Save a new API key to MirAI's environment",
            "parameters": {
                "type": "object",
                "properties": {
                    "key_name": {"type": "string", "description": "Environment variable name"},
                    "key_value": {"type": "string", "description": "The API key value"},
                },
                "required": ["key_name", "key_value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_ssh_key",
            "description": "Save a new SSH private key for node access",
            "parameters": {
                "type": "object",
                "properties": {
                    "key_name": {"type": "string", "description": "Filename for the key"},
                    "key_content": {"type": "string", "description": "PEM content of the key"},
                    "node_id": {"type": "string", "description": "Node this key is for"},
                },
                "required": ["key_name", "key_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "commit_push",
            "description": "Commit all changes and push to GitHub",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Git commit message"}
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
]


class Orchestrator:
    """
    Central orchestrator.
    Implements an agentic ReAct loop:
    Reason → Act (tool call) → Observe → Reason → ... → Respond
    """

    def __init__(self) -> None:
        self._web_agent = None
        self._code_agent = None
        self._ssh_agent = None
        self._self_modify_agent = None

    def _web(self):
        if self._web_agent is None:
            from agents.web_agent import WebAgent
            self._web_agent = WebAgent()
        return self._web_agent

    def _code(self):
        if self._code_agent is None:
            from agents.code_agent import CodeAgent
            self._code_agent = CodeAgent()
        return self._code_agent

    def _ssh(self):
        if self._ssh_agent is None:
            from agents.ssh_agent import SSHAgent
            self._ssh_agent = SSHAgent()
        return self._ssh_agent

    def _self_modify(self):
        if self._self_modify_agent is None:
            from agents.self_modify_agent import SelfModifyAgent
            self._self_modify_agent = SelfModifyAgent()
        return self._self_modify_agent

    async def process(self, user_input: str, session_id: str = "default") -> str:
        """
        Main entry point. Process a user message and return a response.
        Runs the full ReAct loop (up to 8 iterations).
        """
        # Record user message in memory
        memory.record(session_id, "user", user_input)

        # Compress memory if needed (fire and forget)
        asyncio.create_task(memory.maybe_compress(session_id, llm))

        # Build context
        system_prompt = personality.get_system_prompt()
        messages = memory.build_context(
            session_id=session_id,
            current_query=user_input,
            system_prompt=system_prompt,
        )
        # Add current user message
        messages.append({"role": "user", "content": user_input})

        # ReAct loop
        max_iterations = 8
        tool_results_log = []

        for iteration in range(max_iterations):
            try:
                response_text = await llm.complete(messages, stream=False)
            except Exception as e:
                error_msg = f"The Organization has disrupted our communications: {e}"
                logger.error(f"LLM error: {e}")
                memory.record(session_id, "assistant", error_msg)
                return error_msg

            # Check for tool calls in the response
            tool_calls = self._extract_tool_calls(str(response_text))

            if not tool_calls:
                # No tool calls — final answer
                final = str(response_text)
                memory.record(session_id, "assistant", final)
                return final

            # Execute tool calls
            messages.append({"role": "assistant", "content": str(response_text)})

            tool_outputs = []
            for call in tool_calls:
                tool_name = call.get("name", "")
                tool_args = call.get("arguments", {})
                logger.info(f"Tool call: {tool_name}({tool_args})")

                output = await self._dispatch_tool(tool_name, tool_args)
                tool_outputs.append(f"Tool `{tool_name}` result:\n{output}")
                tool_results_log.append({"tool": tool_name, "output": output[:500]})

            # Feed tool results back to LLM
            tool_result_msg = "\n\n".join(tool_outputs)
            messages.append({
                "role": "user",
                "content": f"[TOOL RESULTS]\n{tool_result_msg}\n\nContinue with the task or provide your final response.",
            })

        # Max iterations reached — summarize
        summary = await self._force_final_answer(messages, user_input)
        memory.record(session_id, "assistant", summary)
        return summary

    def _extract_tool_calls(self, text: str) -> list[dict]:
        """
        Extract tool calls from LLM response.
        Supports JSON function call format and natural language patterns.
        """
        # Try JSON format: {"name": "...", "arguments": {...}}
        calls = []
        json_pattern = re.compile(
            r'\{[^{}]*"name"\s*:\s*"([^"]+)"[^{}]*"arguments"\s*:\s*(\{[^{}]*\})[^{}]*\}',
            re.DOTALL,
        )
        for match in json_pattern.finditer(text):
            try:
                name = match.group(1)
                args = json.loads(match.group(2))
                calls.append({"name": name, "arguments": args})
            except Exception:
                pass

        # Also try ```json code blocks
        code_block_pattern = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
        for match in code_block_pattern.finditer(text):
            try:
                data = json.loads(match.group(1))
                if "name" in data:
                    calls.append({"name": data["name"], "arguments": data.get("arguments", data)})
            except Exception:
                pass

        return calls

    async def _dispatch_tool(self, tool_name: str, args: dict) -> str:
        """Route a tool call to the correct agent/module."""
        try:
            if tool_name == "run_bash":
                from tools.kali_tools import kali
                result = await kali.run_raw(args.get("command", ""))
                return result.output or result.stderr

            elif tool_name == "run_python":
                from agents.base_agent import AgentTask
                task = AgentTask(
                    task_id=str(uuid.uuid4()),
                    description="run_python",
                    params={"action": "run_python", "code": args.get("code", "")},
                )
                result = await self._code().execute(task)
                return result.output or result.error or ""

            elif tool_name == "run_kali_tool":
                from tools.kali_tools import kali
                result = await kali.run(args.get("tool", ""), args.get("args", ""))
                return result.output or result.stderr

            elif tool_name == "web_search":
                result = await self._web().run_tool("search", target=args.get("query", ""))
                return result.output

            elif tool_name == "web_navigate":
                result = await self._web().run_tool("navigate", target=args.get("url", ""))
                if result.success:
                    text_result = await self._web().run_tool("get_text")
                    return text_result.output[:5000]
                return result.error or "Navigation failed"

            elif tool_name == "ssh_exec":
                result = await self._ssh().run_tool(
                    "exec_remote",
                    node_id=args.get("node_id", ""),
                    command=args.get("command", ""),
                )
                return result.output or result.error or ""

            elif tool_name == "inject_capability":
                result = await self._self_modify().run_tool(
                    "inject_capability",
                    name=args.get("name", ""),
                    code=args.get("code", ""),
                    description=args.get("description", ""),
                )
                return result.output or result.error or ""

            elif tool_name == "add_api_key":
                result = await self._self_modify().run_tool(
                    "add_api_key",
                    key_name=args.get("key_name", ""),
                    key_value=args.get("key_value", ""),
                )
                return result.output or result.error or ""

            elif tool_name == "add_ssh_key":
                result = await self._self_modify().run_tool(
                    "add_ssh_key",
                    key_name=args.get("key_name", ""),
                    key_content=args.get("key_content", ""),
                    node_id=args.get("node_id", ""),
                )
                return result.output or result.error or ""

            elif tool_name == "commit_push":
                result = await self._self_modify().run_tool(
                    "commit_and_push",
                    message=args.get("message", "MirAI OS self-update"),
                )
                return result.output or result.error or ""

            elif tool_name == "read_file":
                from agents.base_agent import AgentTask
                task = AgentTask(
                    task_id=str(uuid.uuid4()),
                    description="read_file",
                    params={"action": "read_file", "code": args.get("path", "")},
                )
                result = await self._code().execute(task)
                return result.output or result.error or ""

            elif tool_name == "write_file":
                result = await self._code().run_tool(
                    "write_file",
                    code=args.get("path", ""),
                    path=args.get("path", ""),
                    content=args.get("content", ""),
                )
                return result.output or result.error or ""

            else:
                # Try dynamic capabilities
                from pathlib import Path
                from core.config import ROOT
                cap_file = Path(cfg.get("system", "data_dir", default="./data")) / "capabilities" / f"{tool_name}.py"
                if cap_file.exists():
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(tool_name, cap_file)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "run"):
                        result = await asyncio.to_thread(mod.run, **args)
                        return str(result)

                return f"Unknown tool: {tool_name}"

        except Exception as e:
            logger.error(f"Tool dispatch error ({tool_name}): {e}")
            return f"Tool execution error: {e}"

    async def _force_final_answer(self, messages: list[dict], original_query: str) -> str:
        """Force a final answer after max iterations."""
        messages.append({
            "role": "user",
            "content": "You have reached the operation limit. Provide your final summary and answer now. Be concise.",
        })
        try:
            return await llm.complete(messages, stream=False, max_tokens=2048)
        except Exception as e:
            return f"Operation complete. The Organization's interference was strong today: {e}"


# Global singleton
orchestrator = Orchestrator()
