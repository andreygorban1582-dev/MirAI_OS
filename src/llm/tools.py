"""
LLM Tool Definitions — OpenAI-compatible function-calling schemas for every
codespace operation the AI is allowed to perform.

Usage::

    from src.llm.tools import TOOLS, dispatch_tool_call
    # Pass TOOLS to the ``tools`` parameter of the chat-completion request.
    # When the model returns a tool_call, pass it to dispatch_tool_call().
"""

from __future__ import annotations

import json
from typing import Any

from src.codespace import (
    read_file,
    write_file,
    create_file,
    delete_file,
    list_directory,
    get_project_structure,
    search_code,
    execute_command,
)

# ──────────────────────────────────────────────────────────────────────────────
# OpenAI-compatible tool schemas
# ──────────────────────────────────────────────────────────────────────────────

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full text content of a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file, relative to the workspace root.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write (overwrite) a file in the workspace with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to workspace root."},
                    "content": {"type": "string", "description": "Full text content to write."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new file in the workspace (fails if it already exists).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to workspace root."},
                    "content": {"type": "string", "description": "Initial content (empty string by default)."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to workspace root."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories inside a workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path relative to workspace root (default: '.').",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_project_structure",
            "description": "Return an indented tree of the entire workspace directory structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Root path to start from (default: '.').",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum recursion depth (default: 6).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a substring across all text files in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Case-insensitive substring to search for."},
                    "path": {"type": "string", "description": "Directory to search in (default: '.')." },
                    "extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of file extensions to restrict the search, e.g. [\".py\", \".md\"].",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": (
                "Execute a shell command inside the workspace and return its output. "
                "Use this for running tests, git commands, package installs, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run."},
                    "cwd": {
                        "type": "string",
                        "description": "Working directory relative to workspace root (default: '.').",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds before the command is killed (default: 30).",
                    },
                },
                "required": ["command"],
            },
        },
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ──────────────────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, Any] = {
    "read_file": read_file,
    "write_file": write_file,
    "create_file": create_file,
    "delete_file": delete_file,
    "list_directory": list_directory,
    "get_project_structure": get_project_structure,
    "search_code": search_code,
    "execute_command": execute_command,
}


def dispatch_tool_call(tool_name: str, arguments: str | dict) -> str:
    """
    Invoke the tool identified by *tool_name* with *arguments* and return
    the result serialised as a JSON string (suitable for the ``tool`` role
    message content in a chat-completion request).

    *arguments* may be a raw JSON string (as returned by the model) or an
    already-parsed dict.
    """
    if tool_name not in _REGISTRY:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    if isinstance(arguments, str):
        try:
            kwargs: dict = json.loads(arguments)
        except json.JSONDecodeError as exc:
            return json.dumps({"error": f"Invalid JSON in tool arguments: {exc}"})
    else:
        kwargs = arguments
    try:
        result = _REGISTRY[tool_name](**kwargs)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})
