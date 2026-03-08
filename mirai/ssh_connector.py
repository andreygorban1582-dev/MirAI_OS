"""
mirai/ssh_connector.py
──────────────────────
Codespace SSH Connector
═════════════════════════════════════════════════════════════════════════════
What this module does
─────────────────────
• Opens an SSH connection to a remote host (e.g. a GitHub Codespace or a
  cloud VM) using Paramiko.
• Allows the agent to run commands on the remote machine and stream the
  output back.
• Supports key-based and password-based authentication.
• Useful when you want MirAI running on a remote server while you interact
  with it via Telegram from your Legion Go.

Typical use case
────────────────
  1. Spin up a GitHub Codespace with the MirAI_OS repository.
  2. Set SSH_HOST / SSH_USER / SSH_KEY_PATH in .env.
  3. MirAI can then use this connector to execute commands on the Codespace
     and bring results back to the local conversation.
"""

from __future__ import annotations

from typing import Optional, Tuple

from loguru import logger

from mirai.settings import settings

try:
    import paramiko

    _PARAMIKO_AVAILABLE = True
except ImportError:
    _PARAMIKO_AVAILABLE = False
    logger.debug("paramiko not installed – SSH connector disabled.")


class SSHConnector:
    """
    Thin wrapper around paramiko for remote command execution.

    Parameters
    ----------
    host : str, optional
        SSH server hostname/IP.  Defaults to settings.ssh_host.
    user : str, optional
        SSH username.  Defaults to settings.ssh_user.
    key_path : str, optional
        Path to private key file.  Defaults to settings.ssh_key_path.
    port : int, optional
        SSH port.  Defaults to settings.ssh_port.
    """

    def __init__(
        self,
        host: str | None = None,
        user: str | None = None,
        key_path: str | None = None,
        port: int | None = None,
    ) -> None:
        self._host = host or settings.ssh_host
        self._user = user or settings.ssh_user
        self._key_path = key_path or settings.ssh_key_path
        self._port = port or settings.ssh_port
        self._client: Optional[object] = None

    def connect(self) -> bool:
        """
        Open the SSH connection.

        Returns True on success.
        """
        if not _PARAMIKO_AVAILABLE:
            logger.error("paramiko not installed – cannot connect via SSH.")
            return False
        if not self._host:
            logger.warning("SSH_HOST is not set.")
            return False

        import os

        client = paramiko.SSHClient()
        # Use RejectPolicy so unknown hosts raise an exception rather than
        # silently accepting them (which would be vulnerable to MITM attacks).
        # The user should add trusted hosts to ~/.ssh/known_hosts first.
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())  # type: ignore[attr-defined]
        try:
            key_path = os.path.expanduser(self._key_path)
            client.connect(
                hostname=self._host,
                port=self._port,
                username=self._user,
                key_filename=key_path if os.path.exists(key_path) else None,
                timeout=15,
            )
            self._client = client
            logger.info(f"SSH connected to {self._user}@{self._host}:{self._port}")
            return True
        except Exception as exc:
            logger.error(f"SSH connect failed: {exc}")
            return False

    def run(self, command: str) -> Tuple[str, str, int]:
        """
        Execute `command` on the remote host.

        Returns
        -------
        tuple(stdout, stderr, exit_code)
        """
        if not self._client:
            if not self.connect():
                return "", "SSH not connected.", -1
        try:
            _, stdout, stderr = self._client.exec_command(command, timeout=60)  # type: ignore[union-attr]
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            rc = stdout.channel.recv_exit_status()
            return out, err, rc
        except Exception as exc:
            logger.error(f"SSH exec failed: {exc}")
            return "", str(exc), -1

    def close(self) -> None:
        if self._client:
            self._client.close()  # type: ignore[union-attr]
            self._client = None
            logger.info("SSH connection closed.")

    def __enter__(self) -> "SSHConnector":
        self.connect()
        return self

    def __exit__(self, *args) -> None:
        self.close()
