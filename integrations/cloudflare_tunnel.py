"""
MirAI OS — Cloudflare Tunnel Integration (Optional)
Exposes MirAI's internal API to the internet without port forwarding.
100% Free — no account needed for quick tunnels.
Permanent tunnels require free Cloudflare account.

Enable: set CLOUDFLARE_TUNNEL_TOKEN in .env (for permanent tunnel)
        OR set integrations.cloudflare.quick_tunnel: true for temporary URL

Without Cloudflare: MirAI only accessible on local network.
With Cloudflare:    MirAI accessible from anywhere via HTTPS URL.

Use cases:
  - Access MirAI from phone when away from home
  - Webhook endpoints for integrations
  - Remote team access
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("mirai.integrations.cloudflare")


class CloudflareTunnel:
    """Manages a Cloudflare tunnel for external access."""

    def __init__(self) -> None:
        self.token = os.getenv("CLOUDFLARE_TUNNEL_TOKEN", "")
        self.quick_tunnel = os.getenv("CLOUDFLARE_QUICK_TUNNEL", "false").lower() == "true"
        self.local_port = int(os.getenv("MIRAI_API_PORT", "8080"))
        self._process: Optional[subprocess.Popen] = None
        self._public_url: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.token) or self.quick_tunnel

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def public_url(self) -> Optional[str]:
        return self._public_url

    async def start(self) -> Optional[str]:
        """Start tunnel. Returns public URL."""
        if self.is_running():
            return self._public_url

        if not self._is_cloudflared_installed():
            await self._install_cloudflared()

        if self.token:
            return await self._start_named_tunnel()
        elif self.quick_tunnel:
            return await self._start_quick_tunnel()
        else:
            logger.warning("Cloudflare tunnel not configured")
            return None

    async def _start_quick_tunnel(self) -> Optional[str]:
        """Start a temporary cloudflared quick tunnel (no account needed)."""
        logger.info(f"Starting Cloudflare quick tunnel for port {self.local_port}...")
        try:
            self._process = await asyncio.create_subprocess_exec(
                "cloudflared", "tunnel", "--url", f"http://localhost:{self.local_port}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            # Read stderr to find tunnel URL
            for _ in range(30):
                line = await asyncio.wait_for(self._process.stderr.readline(), timeout=5)
                line_str = line.decode("utf-8", errors="replace")
                match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line_str)
                if match:
                    self._public_url = match.group(0)
                    logger.info(f"Cloudflare quick tunnel: {self._public_url}")
                    return self._public_url
        except Exception as e:
            logger.error(f"Quick tunnel failed: {e}")
        return None

    async def _start_named_tunnel(self) -> Optional[str]:
        """Start a named tunnel with Cloudflare token (permanent URL)."""
        logger.info("Starting named Cloudflare tunnel...")
        try:
            self._process = await asyncio.create_subprocess_exec(
                "cloudflared", "tunnel", "run", "--token", self.token,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._public_url = "[configured via Cloudflare dashboard]"
            logger.info("Named Cloudflare tunnel running.")
            return self._public_url
        except Exception as e:
            logger.error(f"Named tunnel failed: {e}")
        return None

    def stop(self) -> None:
        if self._process:
            self._process.terminate()
            self._process = None
            self._public_url = None
            logger.info("Cloudflare tunnel stopped.")

    def _is_cloudflared_installed(self) -> bool:
        import shutil
        return shutil.which("cloudflared") is not None

    async def _install_cloudflared(self) -> None:
        """Auto-install cloudflared on Linux/WSL."""
        logger.info("Installing cloudflared...")
        cmd = (
            "curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/"
            "cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && "
            "chmod +x /usr/local/bin/cloudflared"
        )
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        if self._is_cloudflared_installed():
            logger.info("cloudflared installed successfully.")
        else:
            logger.error("cloudflared install failed — install manually: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/")


# Global singleton
cloudflare_tunnel = CloudflareTunnel()
