"""
SSH Connector – connects to remote hosts / GitHub Codespaces via SSH.
Supports interactive command execution and file transfer.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

import config

logger = logging.getLogger(__name__)


class SSHConnector:
    """SSH client wrapper using paramiko."""

    def __init__(self) -> None:
        self.host = config.SSH_HOST
        self.port = config.SSH_PORT
        self.user = config.SSH_USER
        self.key_path = Path(os.path.expanduser(config.SSH_KEY_PATH))
        self._client: Optional[object] = None

    # ── connection ────────────────────────────────────────────────────────────

    def connect(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        key_path: Optional[str] = None,
    ) -> bool:
        """Open an SSH connection. Returns True on success.

        Only hosts present in ~/.ssh/known_hosts (or the system host key
        store) are accepted. To add a new host, run:
            ssh-keyscan <host> >> ~/.ssh/known_hosts
        """
        try:
            import paramiko  # type: ignore

            client = paramiko.SSHClient()
            client.load_system_host_keys()
            try:
                client.load_host_keys(
                    os.path.expanduser("~/.ssh/known_hosts")
                )
            except FileNotFoundError:
                pass
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
            client.connect(
                hostname=host or self.host,
                port=port or self.port,
                username=user or self.user,
                key_filename=str(key_path or self.key_path),
                timeout=10,
            )
            self._client = client
            logger.info("SSH connected to %s", host or self.host)
            return True
        except ImportError:
            logger.error("paramiko not installed – SSH disabled.")
            return False
        except Exception as exc:
            logger.error("SSH connect error: %s", exc)
            return False

    def disconnect(self) -> None:
        if self._client is not None:
            try:
                self._client.close()  # type: ignore[attr-defined]
            except Exception:
                pass
            self._client = None

    def is_connected(self) -> bool:
        if self._client is None:
            return False
        transport = self._client.get_transport()  # type: ignore[attr-defined]
        return transport is not None and transport.is_active()

    # ── execution ─────────────────────────────────────────────────────────────

    def run(self, command: str, timeout: int = 30) -> Tuple[str, str, int]:
        """Execute a command. Returns (stdout, stderr, exit_code)."""
        if not self.is_connected():
            return "", "Not connected", -1
        try:
            _, stdout, stderr = self._client.exec_command(  # type: ignore[attr-defined]
                command, timeout=timeout
            )
            out = stdout.read().decode(errors="replace").strip()
            err = stderr.read().decode(errors="replace").strip()
            code = stdout.channel.recv_exit_status()
            return out, err, code
        except Exception as exc:
            logger.error("SSH run error: %s", exc)
            return "", str(exc), -1

    # ── file transfer ─────────────────────────────────────────────────────────

    def upload(self, local: str, remote: str) -> bool:
        """Upload a local file to the remote host via SFTP."""
        if not self.is_connected():
            return False
        try:
            sftp = self._client.open_sftp()  # type: ignore[attr-defined]
            sftp.put(local, remote)
            sftp.close()
            return True
        except Exception as exc:
            logger.error("SFTP upload error: %s", exc)
            return False

    def download(self, remote: str, local: str) -> bool:
        """Download a remote file to the local host via SFTP."""
        if not self.is_connected():
            return False
        try:
            sftp = self._client.open_sftp()  # type: ignore[attr-defined]
            sftp.get(remote, local)
            sftp.close()
            return True
        except Exception as exc:
            logger.error("SFTP download error: %s", exc)
            return False
