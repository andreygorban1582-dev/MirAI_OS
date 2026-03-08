"""
mirai/anonymity.py
──────────────────
Anonymity Layer – Tor Integration & Identity Rotation
═════════════════════════════════════════════════════════════════════════════
What this module does
─────────────────────
• Configures Python's requests session to route all traffic through the local
  Tor SOCKS5 proxy (127.0.0.1:9050 by default).
• Uses the Tor control port (via `stem`) to send a NEWNYM signal, rotating
  the circuit and obtaining a new exit-node IP address.
• Rotates identities automatically on a configurable schedule.
• Provides an `anonymous_get()` convenience function that fetches a URL
  through Tor and returns the response text.
• Warns clearly (and does NOT crash) when Tor is disabled or unavailable.

Privacy model
─────────────
Every outbound HTTP/HTTPS request made through `get_session()` is tunnelled
through the Tor network.  This hides the host machine's real IP from remote
servers.  Note that Tor does NOT protect against endpoint-level tracking
(e.g. logging into the same account) – it only provides network anonymity.
"""

from __future__ import annotations

import time
from threading import Thread, Event
from typing import Optional

import requests
from loguru import logger

from mirai.settings import settings

try:
    from stem import Signal
    from stem.control import Controller

    _STEM_AVAILABLE = True
except ImportError:
    _STEM_AVAILABLE = False
    logger.warning("stem library not installed – Tor circuit rotation disabled.")


# ── Session factory ───────────────────────────────────────────────────────────

def get_session() -> requests.Session:
    """
    Return a requests.Session pre-configured to use the Tor SOCKS5 proxy.

    If Tor is disabled in settings the session falls back to a normal
    (un-proxied) session.
    """
    session = requests.Session()
    if settings.tor_enabled:
        proxy_url = f"socks5h://127.0.0.1:{settings.tor_socks_port}"
        session.proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }
        # Randomise User-Agent to reduce browser fingerprinting
        session.headers.update({"User-Agent": _random_ua()})
        logger.debug(f"Session routed through Tor SOCKS5 proxy on port {settings.tor_socks_port}")
    else:
        logger.debug("Tor disabled – using direct connection.")
    return session


def anonymous_get(url: str, **kwargs) -> requests.Response:
    """
    Fetch `url` through Tor and return the Response object.

    Parameters
    ----------
    url : str
        The URL to fetch.
    **kwargs
        Forwarded to requests.Session.get().
    """
    session = get_session()
    return session.get(url, timeout=kwargs.pop("timeout", 30), **kwargs)


# ── Circuit rotation ──────────────────────────────────────────────────────────

def rotate_identity() -> bool:
    """
    Send a NEWNYM signal to Tor, requesting a new circuit / exit node.

    Returns
    -------
    bool
        True if the rotation succeeded, False otherwise.
    """
    if not settings.tor_enabled:
        logger.info("Tor is disabled – skipping identity rotation.")
        return False

    if not _STEM_AVAILABLE:
        logger.warning("stem not available – cannot rotate Tor identity.")
        return False

    try:
        with Controller.from_port(port=settings.tor_control_port) as ctrl:
            if settings.tor_password:
                ctrl.authenticate(password=settings.tor_password)
            else:
                ctrl.authenticate()
            ctrl.signal(Signal.NEWNYM)
            logger.info("Tor identity rotated (NEWNYM signal sent).")
            # Tor spec says to wait ≥1 s before using the new circuit
            time.sleep(1)
            return True
    except Exception as exc:
        logger.warning(f"Could not rotate Tor identity: {exc}")
        return False


def get_current_ip() -> str:
    """Return the current exit-node IP as seen by an external service."""
    try:
        resp = anonymous_get("https://api.ipify.org", timeout=15)
        return resp.text.strip()
    except Exception as exc:
        return f"[unknown – {exc}]"


# ── Auto-rotation scheduler ───────────────────────────────────────────────────

class IdentityRotator:
    """
    Background thread that rotates the Tor identity every N seconds.

    Usage::

        rotator = IdentityRotator()
        rotator.start()
        # … do work …
        rotator.stop()
    """

    def __init__(self, interval: int | None = None) -> None:
        self._interval = interval or settings.tor_rotate_every
        self._stop_event = Event()
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        if not settings.tor_enabled:
            logger.info("Tor disabled – IdentityRotator will not start.")
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run, daemon=True, name="tor-rotator")
        self._thread.start()
        logger.info(f"Tor identity auto-rotation started (every {self._interval}s).")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Tor identity auto-rotation stopped.")

    def _run(self) -> None:
        while not self._stop_event.wait(timeout=self._interval):
            rotate_identity()


# ── Internal helpers ──────────────────────────────────────────────────────────

_USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "curl/8.7.1",
]


def _random_ua() -> str:
    import random
    return random.choice(_USER_AGENTS)
