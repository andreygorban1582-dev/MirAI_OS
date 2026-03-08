"""
Kali Linux Integration – runs security commands inside a Kali Docker container
or a native Kali environment (if available).
"""

from __future__ import annotations

import logging
import shutil
import subprocess  # noqa: S404
from typing import Optional

import config

logger = logging.getLogger(__name__)


class KaliIntegration:
    """Execute security / penetration-testing commands via Kali Linux."""

    def __init__(self) -> None:
        self.enabled = config.KALI_ENABLED
        self.image = config.KALI_DOCKER_IMAGE
        self._docker_available: Optional[bool] = None

    # ── public API ────────────────────────────────────────────────────────────

    def run(self, command: str, timeout: int = 30) -> str:
        """Run a command in Kali Linux and return stdout/stderr."""
        if not self.enabled:
            return "Kali integration is disabled. Set KALI_ENABLED=true to enable."
        if self._has_docker():
            return self._run_docker(command, timeout)
        return self._run_native(command, timeout)

    def nmap_scan(self, target: str, flags: str = "-sV --open") -> str:
        """Convenience wrapper for nmap scanning."""
        return self.run(f"nmap {flags} {target}")

    def whois_lookup(self, domain: str) -> str:
        """WHOIS lookup for a domain or IP."""
        return self.run(f"whois {domain}")

    # ── backends ──────────────────────────────────────────────────────────────

    def _has_docker(self) -> bool:
        if self._docker_available is None:
            self._docker_available = shutil.which("docker") is not None
        return self._docker_available  # type: ignore[return-value]

    def _run_docker(self, command: str, timeout: int) -> str:
        cmd = [
            "docker", "run", "--rm",
            self.image,
            "bash", "-c", command,
        ]
        return self._exec(cmd, timeout)

    def _run_native(self, command: str, timeout: int) -> str:
        return self._exec(["bash", "-c", command], timeout)

    @staticmethod
    def _exec(cmd: list, timeout: int) -> str:
        try:
            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = (result.stdout + result.stderr).strip()
            return output if output else "(no output)"
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s."
        except Exception as exc:
            logger.error("Kali exec error: %s", exc)
            return f"Error: {exc}"
