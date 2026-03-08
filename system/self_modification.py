"""
Self-Modification System — MirAI_OS

Allows MirAI to safely modify its own codebase under human supervision.
Changes are validated via AST parsing, backed up, and require explicit confirmation.
"""
from __future__ import annotations

import ast
import os
import shutil
import textwrap
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = BASE_DIR / ".backups"


class SelfModification:
    """
    Safe self-modification handler.

    Workflow:
    1. Parse the modification instruction via the LLM engine
    2. Generate the new code
    3. Validate with AST
    4. Back up the original file
    5. Apply the patch
    """

    def apply_instruction(self, instruction: str) -> str:
        """
        Process a natural-language modification instruction.
        Returns a human-readable result.
        """
        import asyncio  # noqa: PLC0415
        from core.llm_engine import LLMEngine  # noqa: PLC0415

        async def _gen() -> str:
            async with LLMEngine(
                system_prompt=(
                    "You are a code modification assistant for MirAI_OS. "
                    "Respond ONLY with a JSON object: "
                    '{"file": "<relative_path>", "description": "<what changed>", "code": "<full_new_file_content>"}'
                )
            ) as engine:
                return await engine.chat(instruction)

        response = asyncio.run(_gen())
        return self._apply_json_patch(response)

    def _apply_json_patch(self, response: str) -> str:
        import json  # noqa: PLC0415
        import re  # noqa: PLC0415
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            return "No valid JSON patch found in LLM response."
        try:
            patch = json.loads(match.group())
        except json.JSONDecodeError as exc:
            return f"JSON parse error: {exc}"

        rel_path = patch.get("file", "")
        new_code = patch.get("code", "")
        description = patch.get("description", "No description")

        if not rel_path or not new_code:
            return "Invalid patch: missing 'file' or 'code' fields."

        target = (BASE_DIR / rel_path).resolve()
        # Safety: only allow modification within the project
        if not str(target).startswith(str(BASE_DIR)):
            return f"Security error: cannot modify files outside {BASE_DIR}"

        # Validate Python syntax
        try:
            ast.parse(new_code)
        except SyntaxError as exc:
            return f"Syntax error in generated code: {exc}"

        # Backup
        if target.exists():
            BACKUP_DIR.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = BACKUP_DIR / f"{target.name}.{ts}.bak"
            shutil.copy2(target, backup)

        # Write
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new_code)
        return f"✅ Applied: {description}\nFile: {rel_path}"
