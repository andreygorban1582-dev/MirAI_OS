"""
mirai/__init__.py
─────────────────
Package initialiser for MirAI_OS.

Exposes the top-level version string and the main Agent class so callers can
simply do:

    from mirai import Agent, __version__
"""

__version__ = "1.0.0"
__author__ = "MirAI_OS contributors"

from mirai.agent import Agent  # noqa: F401 – re-exported for convenience

__all__ = ["Agent", "__version__"]
