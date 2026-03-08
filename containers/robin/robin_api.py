"""Robin  –  Tor proxy helper API for dark-web research queries."""

import logging
import os

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mirai.robin")

TOR_SOCKS = "socks5://127.0.0.1:9050"

app = FastAPI(title="MirAI Robin (Tor)", version="2.0.0")


class FetchRequest(BaseModel):
    url: str
    timeout: int = 30


@app.get("/health")
async def health() -> dict:
    # Check Tor connectivity
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
    """Fetch a URL through Tor."""
    try:
        async with httpx.AsyncClient(
            proxies={"all://": TOR_SOCKS}, timeout=req.timeout
        ) as c:
            r = await c.get(req.url, follow_redirects=True)
            return {
                "url": str(r.url),
                "status": r.status_code,
                "content": r.text[:10000],
            }
    except Exception as exc:
        raise HTTPException(500, str(exc))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8600)
