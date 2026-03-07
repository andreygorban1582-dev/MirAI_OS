"""
Codespace Connector — gives the AI full read/write/execute access to the
repository it is running inside (i.e. the GitHub Codespace workspace).

All operations are scoped to WORKSPACE_ROOT so the AI cannot escape the
repository directory.
"""

from __future__ import annotations

import os
import subprocess
import fnmatch
from pathlib import Path
from typing import Optional

WORKSPACE_ROOT = Path(os.environ.get("GITHUB_WORKSPACE", Path(__file__).resolve().parents[2]))

# Patterns that are never exposed to the AI for safety reasons
_EXCLUDED = {".git", "__pycache__", "*.pyc", "node_modules", ".env"}


def _safe_path(rel_or_abs: str) -> Path:
    """Resolve a path and ensure it stays inside WORKSPACE_ROOT."""
    target = (WORKSPACE_ROOT / rel_or_abs).resolve()
    if not str(target).startswith(str(WORKSPACE_ROOT)):
        raise PermissionError(f"Path '{rel_or_abs}' is outside the workspace root.")
    return target


def _is_excluded(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in _EXCLUDED)


# ──────────────────────────────────────────────────────────────────────────────
# File-system operations
# ──────────────────────────────────────────────────────────────────────────────

def read_file(path: str) -> str:
    """Return the text content of *path* (relative to workspace root)."""
    target = _safe_path(path)
    return target.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    """Write *content* to *path*, creating parent directories as needed."""
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Written {len(content)} characters to {target.relative_to(WORKSPACE_ROOT)}"


def create_file(path: str, content: str = "") -> str:
    """Create a new file at *path* with optional *content*."""
    target = _safe_path(path)
    if target.exists():
        return f"File already exists: {target.relative_to(WORKSPACE_ROOT)}"
    return write_file(path, content)


def delete_file(path: str) -> str:
    """Delete the file at *path*."""
    target = _safe_path(path)
    if not target.exists():
        return f"File not found: {path}"
    target.unlink()
    return f"Deleted {target.relative_to(WORKSPACE_ROOT)}"


def list_directory(path: str = ".") -> list[dict]:
    """Return a list of entries in *path* with name, type, and size."""
    target = _safe_path(path)
    if not target.is_dir():
        raise NotADirectoryError(f"{path} is not a directory.")
    entries = []
    for entry in sorted(target.iterdir()):
        if _is_excluded(entry.name):
            continue
        entries.append(
            {
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else None,
            }
        )
    return entries


def get_project_structure(path: str = ".", _depth: int = 0, max_depth: int = 6) -> str:
    """Return an indented tree of the workspace, up to *max_depth* levels deep."""
    if _depth > max_depth:
        return ""
    target = _safe_path(path)
    lines: list[str] = []
    for entry in sorted(target.iterdir()):
        if _is_excluded(entry.name):
            continue
        indent = "  " * _depth
        if entry.is_dir():
            lines.append(f"{indent}{entry.name}/")
            subtree = get_project_structure(
                str(entry.relative_to(WORKSPACE_ROOT)), _depth + 1, max_depth
            )
            if subtree:
                lines.append(subtree)
        else:
            lines.append(f"{indent}{entry.name}")
    return "\n".join(lines)


def search_code(query: str, path: str = ".", extensions: Optional[list[str]] = None) -> list[dict]:
    """
    Search for *query* (case-insensitive substring) in all text files under
    *path*.  Optionally restrict to files with given *extensions*
    (e.g. ``[".py", ".md"]``).
    """
    target = _safe_path(path)
    results: list[dict] = []
    exts = set(extensions) if extensions else None
    for fpath in sorted(target.rglob("*")):
        if not fpath.is_file():
            continue
        if any(_is_excluded(part) for part in fpath.parts):
            continue
        if exts and fpath.suffix not in exts:
            continue
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if query.lower() in line.lower():
                results.append(
                    {
                        "file": str(fpath.relative_to(WORKSPACE_ROOT)),
                        "line": lineno,
                        "content": line.rstrip(),
                    }
                )
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Command execution
# ──────────────────────────────────────────────────────────────────────────────

def execute_command(
    command: str,
    cwd: str = ".",
    timeout: int = 30,
    capture_stderr: bool = True,
) -> dict:
    """
    Run *command* in a subprocess inside the workspace.

    Returns a dict with keys ``returncode``, ``stdout``, and ``stderr``.
    The working directory is set to *cwd* (relative to workspace root).
    """
    cwd_path = _safe_path(cwd)
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        if capture_stderr and stderr:
            stdout = stdout + stderr
            stderr = ""
        return {
            "returncode": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds.",
        }
    except Exception as exc:
        return {"returncode": -1, "stdout": "", "stderr": str(exc)}
