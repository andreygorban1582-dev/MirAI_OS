"""
MirAI OS — Ngrok Tunnel Integration (Optional)
Instant public HTTPS URL for your Legion Go — no port forwarding.
Free tier: 1 active tunnel, random URL each restart.
Paid tier: Static subdomain (your-mirai.ngrok.io)

Enable: set NGROK_AUTH_TOKEN in .env
        set integrations.ngrok.enabled: true in settings.yaml

Without Ngrok: MirAI only on local network.
With Ngrok:    Instant public URL — usable as webhook endpoint.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger("mirai.integrations.ngrok")


class NgrokTunnel:
    """Manages ngrok tunnel for public access."""

    def __init__(self) -> None:
        self.auth_token = os.getenv("NGROK_AUTH_TOKEN", "")
        self.enabled = bool(self.auth_token)
        self.local_port = int(os.getenv("MIRAI_API_PORT", "8080"))
        self.domain = os.getenv("NGROK_DOMAIN", "")  # Paid: static domain
        self._tunnel = None
        self._public_url: Optional[str] = None

    def is_available(self) -> bool:
        return self.enabled

    @property
    def public_url(self) -> Optional[str]:
        return self._public_url

    async def start(self) -> Optional[str]:
        """Start ngrok tunnel. Returns public URL."""
        if not self.is_available():
            logger.warning("Ngrok not configured — add NGROK_AUTH_TOKEN to .env")
            return None
        try:
            import ngrok
            listener = await asyncio.to_thread(
                ngrok.forward,
                self.local_port,
                authtoken=self.auth_token,
                domain=self.domain or None,
            )
            self._public_url = listener.url()
            self._tunnel = listener
            logger.info(f"Ngrok tunnel: {self._public_url}")
            return self._public_url
        except ImportError:
            return await self._start_cli_tunnel()
        except Exception as e:
            logger.error(f"Ngrok start error: {e}")
            return None

    async def _start_cli_tunnel(self) -> Optional[str]:
        """Fallback: use ngrok CLI."""
        import shutil, re, json
        if not shutil.which("ngrok"):
            logger.error("ngrok not installed. Install from https://ngrok.com/download")
            return None
        proc = await asyncio.create_subprocess_exec(
            "ngrok", "http", str(self.local_port),
            "--authtoken", self.auth_token,
            "--log=stdout", "--log-format=json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        self._tunnel = proc
        for _ in range(30):
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=3)
            try:
                data = json.loads(line)
                url = data.get("url", "")
                if url.startswith("https"):
                    self._public_url = url
                    return url
            except Exception:
                pass
        return None

    def stop(self) -> None:
        if self._tunnel:
            try:
                if hasattr(self._tunnel, "close"):
                    self._tunnel.close()
                elif hasattr(self._tunnel, "terminate"):
                    self._tunnel.terminate()
            except Exception:
                pass
            self._tunnel = None
            self._public_url = None


# Global singleton
ngrok_tunnel = NgrokTunnel()
