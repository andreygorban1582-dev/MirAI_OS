"""Robin  –  Tor proxy helper API for dark-web research queries."""

import ipaddress
import logging
import re
from urllib.parse import urlparse

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mirai.robin")

TOR_SOCKS = "socks5://127.0.0.1:9050"

# Private/loopback ranges that must never be fetched (SSRF protection)
_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

_ONION_RE = re.compile(r"^[a-z2-7]{16,56}\.onion$", re.IGNORECASE)


def _validate_url(url: str) -> str:
    """
    Validate that the URL:
    1. Is a well-formed HTTP/HTTPS URL.
    2. Does NOT target a private/loopback host (prevents SSRF against
       internal Docker services or the host network).
    Returns a reconstructed URL built from validated components.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(400, "Malformed URL")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, "Only http:// and https:// URLs are allowed")

    hostname = parsed.hostname or ""
    if not hostname:
        raise HTTPException(400, "URL has no hostname")

    # Allow .onion addresses (they route through Tor only)
    if _ONION_RE.match(hostname):
        # Reconstruct from validated parts; .onion never resolves outside Tor
        safe_scheme = parsed.scheme  # validated above: 'http' or 'https'
        safe_host   = hostname        # validated: matches .onion pattern
        safe_path   = parsed.path or "/"
        safe_query  = parsed.query
        reconstructed = f"{safe_scheme}://{safe_host}{safe_path}"
        if safe_query:
            reconstructed += f"?{safe_query}"
        return reconstructed

    # Block raw IP addresses pointing at private ranges
    try:
        addr = ipaddress.ip_address(hostname)
        for net in _PRIVATE_NETS:
            if addr in net:
                raise HTTPException(
                    403,
                    "Requests to private/loopback addresses are not allowed",
                )
        # Public IP – reconstruct from validated parts
        safe_scheme = parsed.scheme
        safe_host   = str(addr)
        safe_path   = parsed.path or "/"
        safe_query  = parsed.query
    except ValueError:
        # hostname is a domain name
        _blocked_hosts = {"localhost", "metadata.google.internal"}
        if hostname.lower() in _blocked_hosts:
            raise HTTPException(403, "Requests to internal hosts are not allowed")
        safe_scheme = parsed.scheme
        safe_host   = hostname
        safe_path   = parsed.path or "/"
        safe_query  = parsed.query

    reconstructed = f"{safe_scheme}://{safe_host}{safe_path}"
    if safe_query:
        reconstructed += f"?{safe_query}"
    return reconstructed


app = FastAPI(title="MirAI Robin (Tor)", version="2.0.0")


class FetchRequest(BaseModel):
    url: str
    timeout: int = 30


@app.get("/health")
async def health() -> dict:
    # Check Tor connectivity using the hardcoded Tor check URL (not user-supplied)
    try:
        async with httpx.AsyncClient(
            proxies={"all://": TOR_SOCKS}, timeout=15
        ) as c:
            r = await c.get("https://check.torproject.org/api/ip")
            data = r.json()
            return {"status": "ok", "tor": data.get("IsTor", False), "ip": data.get("IP")}
    except Exception as exc:
        return {"status": "degraded", "error": str(exc)}


@app.post("/fetch")
async def fetch(req: FetchRequest) -> dict:
    """Fetch a URL through Tor (SSRF-safe: private/loopback hosts are blocked)."""
    safe_url = _validate_url(req.url)
    try:
        async with httpx.AsyncClient(
            proxies={"all://": TOR_SOCKS}, timeout=req.timeout
        ) as c:
            r = await c.get(safe_url, follow_redirects=True)
            return {
                "url": str(r.url),
                "status": r.status_code,
                "content": r.text[:10000],
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8600)
