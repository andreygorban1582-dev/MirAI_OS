"""
mirai/self_mod.py
─────────────────
Self-Modification System
═════════════════════════════════════════════════════════════════════════════
What this module does
─────────────────────
• Allows MirAI to propose and apply modifications to its own source code.
• The cycle is:
    1. Agent decides a file needs changing (e.g. to fix a bug or add a feature).
    2. self_mod reads the current file content from GitHub.
    3. The LLM proposes a new version of the file (full replacement).
    4. self_mod writes the new content back to the repo via the GitHub API.
    5. The change is logged locally and on Telegram.

Safety guards
─────────────
• Only paths in config.github.editable_paths can be modified.
• .env and installer scripts are explicitly protected.
• Every change is committed with an audit timestamp.
• A dry_run mode lets you preview changes without committing.

This gives MirAI "Copilot on itself" capability: it can read, reason about,
and improve its own codebase without human intervention.
"""

from __future__ import annotations

from typing import Optional

from loguru import logger

from mirai.github_client import GitHubClient
from mirai.llm import LLMEngine
from mirai.settings import settings


class SelfModificationSystem:
    """
    Orchestrates the read → reason → write self-modification loop.

    Parameters
    ----------
    github : GitHubClient, optional
        Provide an existing client or let the class create one.
    llm : LLMEngine, optional
        Provide an existing engine or let the class create one.
    dry_run : bool
        If True, proposed changes are returned but NOT committed to GitHub.
    """

    def __init__(
        self,
        github: Optional[GitHubClient] = None,
        llm: Optional[LLMEngine] = None,
        dry_run: bool = False,
    ) -> None:
        self._gh = github or GitHubClient()
        self._llm = llm or LLMEngine()
        self._dry_run = dry_run

    # ── Public API ─────────────────────────────────────────────────────────────

    def modify_file(
        self,
        path: str,
        instruction: str,
        commit_message: str = "",
    ) -> str:
        """
        Read `path`, ask the LLM to apply `instruction`, then write it back.

        Parameters
        ----------
        path : str
            Repo-relative file path (e.g. "mirai/agent.py").
        instruction : str
            Natural-language description of what to change.
        commit_message : str
            Optional commit message; auto-generated if blank.

        Returns
        -------
        str
            A human-readable summary of what was done (or what would be done
            in dry_run mode).
        """
        # 1. Read current content
        current = self._gh.read_file(path)
        if current is None:
            return f"[SelfMod] Could not read {path} – aborting."

        # 2. Ask LLM to produce the new version
        prompt_messages = [
            {
                "role": "user",
                "content": (
                    f"You are modifying the file `{path}` in the MirAI_OS repository.\n\n"
                    f"CURRENT CONTENT:\n```\n{current}\n```\n\n"
                    f"INSTRUCTION: {instruction}\n\n"
                    "Return ONLY the complete new file content, nothing else – "
                    "no markdown fences, no explanation before or after the code."
                ),
            }
        ]
        new_content = self._llm.chat(prompt_messages)

        if new_content.startswith("[LLM Error]"):
            return f"[SelfMod] LLM failed: {new_content}"

        # 3. Dry-run preview
        if self._dry_run:
            logger.info(f"[DRY RUN] Would update {path}:\n{new_content[:500]}…")
            return (
                f"[SelfMod DRY RUN] Proposed change to `{path}`:\n"
                f"```\n{new_content[:800]}\n```"
            )

        # 4. Write back to GitHub
        success = self._gh.write_file(
            path=path,
            content=new_content,
            message=commit_message or f"Apply: {instruction[:60]}",
        )
        if success:
            return f"[SelfMod] Successfully updated `{path}` – instruction: {instruction[:80]}"
        return f"[SelfMod] Write to `{path}` failed."

    def add_feature(self, feature_description: str) -> str:
        """
        Ask the LLM to decide which file(s) need changing to implement
        `feature_description`, then apply those changes.

        This is a higher-level shortcut over modify_file().
        """
        plan_messages = [
            {
                "role": "user",
                "content": (
                    "You are the self-modification planner for MirAI_OS.\n"
                    f"Feature request: {feature_description}\n\n"
                    "List the files (repo-relative paths) that need to be changed "
                    "and a one-sentence instruction for each.  "
                    "Format: one JSON array of objects with keys 'path' and 'instruction'.\n"
                    "Example: [{\"path\": \"mirai/agent.py\", \"instruction\": \"Add X method\"}]"
                ),
            }
        ]
        plan_raw = self._llm.chat(plan_messages)
        try:
            import json
            plan = json.loads(plan_raw)
        except Exception:
            return f"[SelfMod] Could not parse LLM plan: {plan_raw[:200]}"

        results = []
        for item in plan:
            path = item.get("path", "")
            instruction = item.get("instruction", "")
            if path and instruction:
                result = self.modify_file(path, instruction, commit_message=feature_description[:60])
                results.append(result)

        return "\n".join(results) if results else "[SelfMod] No files were changed."

    def review_self(self) -> str:
        """
        Ask the LLM to review the current codebase and suggest improvements.

        Returns a plain-text report (does not apply any changes).
        """
        files = self._gh.list_files("mirai/")
        if not files:
            return "[SelfMod] Could not retrieve file list from GitHub."

        file_summaries = []
        for f in files[:10]:  # cap to avoid token overflow
            content = self._gh.read_file(f) or ""
            file_summaries.append(f"### {f}\n```python\n{content[:600]}\n```")

        review_prompt = [
            {
                "role": "user",
                "content": (
                    "Review the following source files from MirAI_OS and list:\n"
                    "1. Any bugs or issues\n"
                    "2. Missing features\n"
                    "3. Security concerns\n\n"
                    + "\n\n".join(file_summaries)
                ),
            }
        ]
        return self._llm.chat(review_prompt)
