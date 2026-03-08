"""
Codespace SSH Connector — MirAI_OS

Runs commands on a connected GitHub Codespace via SSH.
"""
from __future__ import annotations

from config.settings import settings


class CodespaceSSH:
    """Execute commands on a GitHub Codespace over SSH."""

    def __init__(self) -> None:
        self.host = settings.codespace_ssh_host
        self.user = settings.codespace_ssh_user
        self.key = settings.codespace_ssh_key

    def run(self, command: str, timeout: int = 30) -> str:
        if not self.host:
            return (
                "Codespace SSH not configured. "
                "Set CODESPACE_SSH_HOST, CODESPACE_SSH_USER, CODESPACE_SSH_KEY in .env"
            )
        try:
            import paramiko  # noqa: PLC0415
        except ImportError:
            return "paramiko not installed. Run: pip install paramiko"

        try:
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
            connect_kwargs: dict = dict(
                hostname=self.host,
                username=self.user,
                timeout=10,
            )
            if self.key:
                import io  # noqa: PLC0415
                pkey = paramiko.RSAKey.from_private_key(io.StringIO(self.key))
                connect_kwargs["pkey"] = pkey
            client.connect(**connect_kwargs)
            _, stdout, stderr = client.exec_command(command, timeout=timeout)
            out = stdout.read().decode(errors="replace")
            err = stderr.read().decode(errors="replace")
            client.close()
            return (out + err).strip() or "(no output)"
        except paramiko.SSHException as exc:
            return (
                f"SSH error: {exc}\n"
                "Tip: add the Codespace host key to your known_hosts file first:\n"
                f"  ssh-keyscan {self.host} >> ~/.ssh/known_hosts"
            )
        except Exception as exc:
            return f"SSH error: {exc}"
