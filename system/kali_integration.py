"""
Kali Linux Integration — MirAI_OS

Connects to a Kali Linux instance via SSH (local or remote) and
executes security/penetration testing tools.
"""
from __future__ import annotations

from config.settings import settings


class KaliIntegration:
    """
    SSH-based Kali Linux executor.

    Configure via environment variables:
      KALI_SSH_HOST, KALI_SSH_USER, KALI_SSH_KEY_PATH
    """

    def __init__(self) -> None:
        self.host = settings.kali_ssh_host
        self.user = settings.kali_ssh_user
        self.key_path = settings.kali_ssh_key_path

    def run_command(self, command: str, timeout: int = 30) -> str:
        """Run a command on the Kali instance and return stdout+stderr."""
        if not self.host:
            return (
                "Kali SSH not configured. "
                "Set KALI_SSH_HOST, KALI_SSH_USER, KALI_SSH_KEY_PATH in .env"
            )

        # Block obviously dangerous commands
        BLOCKED = ["rm -rf /", "mkfs", "dd if=/dev/zero", ":(){:|:&};:"]
        for bad in BLOCKED:
            if bad in command:
                return f"⛔ Blocked dangerous command: {bad}"

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
            if self.key_path:
                connect_kwargs["key_filename"] = self.key_path
            client.connect(**connect_kwargs)
            _, stdout, stderr = client.exec_command(command, timeout=timeout)
            out = stdout.read().decode(errors="replace")
            err = stderr.read().decode(errors="replace")
            client.close()
            return (out + err).strip() or "(no output)"
        except paramiko.SSHException as exc:
            return (
                f"SSH error: {exc}\n"
                "Tip: add the host key to your known_hosts file first:\n"
                f"  ssh-keyscan {self.host} >> ~/.ssh/known_hosts"
            )
        except Exception as exc:
            return f"SSH error: {exc}"
