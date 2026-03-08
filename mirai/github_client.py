"""
mirai/github_client.py
──────────────────────
GitHub Repository Client – Copilot-like Self-Access
═════════════════════════════════════════════════════════════════════════════
What this module does
─────────────────────
• Authenticates against the GitHub API using a Personal Access Token (PAT).
• Provides read / write access to files inside the configured repository.
• Respects the whitelist (editable_paths) and blacklist (protected_paths)
  defined in config.yaml so the agent cannot accidentally overwrite critical
  files like .env or installer scripts.
• All write operations append a timestamped commit message so every change is
  auditable.

Key operations
──────────────
read_file(path)              – return the decoded content of a repo file
write_file(path, content, msg) – create or update a repo file with a commit
list_files(folder)           – list all files in a folder
delete_file(path, msg)       – delete a file from the repo
search_code(query)           – search code in the repo (GitHub code search)

This gives MirAI "Copilot-like" capabilities: it can inspect its own source
code, propose edits to itself, and commit those edits directly via the API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from github import Github, GithubException, Repository
from loguru import logger

from mirai.settings import settings


class GitHubClient:
    """
    High-level wrapper around PyGithub for self-modification operations.

    Parameters
    ----------
    token : str, optional
        GitHub PAT.  Defaults to settings.github_token.
    repo_name : str, optional
        "owner/repo" string.  Defaults to settings.github_repo.
    branch : str, optional
        Target branch.  Defaults to settings.github_branch.
    """

    def __init__(
        self,
        token: str | None = None,
        repo_name: str | None = None,
        branch: str | None = None,
    ) -> None:
        self._token = token or settings.github_token
        self._repo_name = repo_name or settings.github_repo
        self._branch = branch or settings.github_branch

        if not self._token:
            logger.warning(
                "GITHUB_TOKEN is not set – repository write access disabled."
            )
            self._gh: Optional[Github] = None
            self._repo: Optional[Repository.Repository] = None
        else:
            self._gh = Github(self._token)
            try:
                self._repo = self._gh.get_repo(self._repo_name)
                logger.info(f"GitHub client connected to {self._repo_name} [{self._branch}]")
            except GithubException as exc:
                logger.error(f"Could not access repo {self._repo_name}: {exc}")
                self._repo = None

    # ── Read operations ───────────────────────────────────────────────────────

    def read_file(self, path: str) -> Optional[str]:
        """
        Return the decoded string content of `path` in the repo.

        Returns None if the file does not exist or access fails.
        """
        if not self._repo:
            return None
        try:
            contents = self._repo.get_contents(path, ref=self._branch)
            if isinstance(contents, list):
                logger.warning(f"{path} is a directory, not a file.")
                return None
            return contents.decoded_content.decode("utf-8")
        except GithubException as exc:
            logger.error(f"read_file({path}) failed: {exc}")
            return None

    def list_files(self, folder: str = "") -> List[str]:
        """
        Recursively list all file paths inside `folder`.

        Parameters
        ----------
        folder : str
            Repository-relative path (e.g. "mirai/" or "").

        Returns
        -------
        list[str]
            Sorted list of file paths relative to repo root.
        """
        if not self._repo:
            return []
        paths: List[str] = []
        try:
            stack = [folder]
            while stack:
                current = stack.pop()
                contents = self._repo.get_contents(current, ref=self._branch)
                if not isinstance(contents, list):
                    contents = [contents]
                for item in contents:
                    if item.type == "dir":
                        stack.append(item.path)
                    else:
                        paths.append(item.path)
        except GithubException as exc:
            logger.error(f"list_files({folder}) failed: {exc}")
        return sorted(paths)

    # ── Write operations ──────────────────────────────────────────────────────

    def write_file(self, path: str, content: str, message: str = "") -> bool:
        """
        Create or update `path` with `content`.

        Parameters
        ----------
        path : str
            Repo-relative path.
        content : str
            New file content (text).
        message : str
            Commit message.  Auto-generated timestamp is appended.

        Returns
        -------
        bool
            True on success.
        """
        if not self._is_editable(path):
            logger.warning(f"write_file({path}) blocked – path is protected.")
            return False
        if not self._repo:
            return False

        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        commit_msg = f"[MirAI self-mod] {message or f'Update {path}'} [{ts}]"

        try:
            existing = self._repo.get_contents(path, ref=self._branch)
            # File exists – update it
            self._repo.update_file(
                path=path,
                message=commit_msg,
                content=content,
                sha=existing.sha,  # type: ignore[union-attr]
                branch=self._branch,
            )
            logger.info(f"Updated {path} in {self._repo_name}.")
        except GithubException as exc:
            if exc.status == 404:
                # File doesn't exist – create it
                try:
                    self._repo.create_file(
                        path=path,
                        message=commit_msg,
                        content=content,
                        branch=self._branch,
                    )
                    logger.info(f"Created {path} in {self._repo_name}.")
                except GithubException as create_exc:
                    logger.error(f"create_file({path}) failed: {create_exc}")
                    return False
            else:
                logger.error(f"write_file({path}) failed: {exc}")
                return False
        return True

    def delete_file(self, path: str, message: str = "") -> bool:
        """Delete `path` from the repository."""
        if not self._is_editable(path):
            logger.warning(f"delete_file({path}) blocked – path is protected.")
            return False
        if not self._repo:
            return False
        try:
            existing = self._repo.get_contents(path, ref=self._branch)
            ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            self._repo.delete_file(
                path=path,
                message=f"[MirAI self-mod] {message or f'Delete {path}'} [{ts}]",
                sha=existing.sha,  # type: ignore[union-attr]
                branch=self._branch,
            )
            logger.info(f"Deleted {path} from {self._repo_name}.")
            return True
        except GithubException as exc:
            logger.error(f"delete_file({path}) failed: {exc}")
            return False

    # ── Code search ───────────────────────────────────────────────────────────

    def search_code(self, query: str) -> List[dict]:
        """
        Search code within the repository using GitHub's code search API.

        Returns
        -------
        list[dict]
            Each dict has keys "path", "url", "snippet".
        """
        if not self._gh:
            return []
        results = []
        try:
            qualified = f"{query} repo:{self._repo_name}"
            for item in self._gh.search_code(qualified):
                results.append(
                    {
                        "path": item.path,
                        "url": item.html_url,
                        "snippet": item.decoded_content[:200].decode("utf-8", errors="replace")
                        if item.decoded_content is not None
                        else "",
                    }
                )
        except GithubException as exc:
            logger.error(f"search_code failed: {exc}")
        return results

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _is_editable(self, path: str) -> bool:
        """Return True if `path` is allowed to be written."""
        # Check protected list first (deny wins)
        for protected in settings.github_protected_paths:
            if path == protected or path.startswith(protected):
                return False
        # Check editable whitelist
        for editable in settings.github_editable_paths:
            if path == editable or path.startswith(editable):
                return True
        # If no whitelist match, deny by default
        return False

    def is_connected(self) -> bool:
        """Return True if the client has a valid repo connection."""
        return self._repo is not None
