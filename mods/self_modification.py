"""
MirAI_OS Self-Modification Module
Allows MirAI to update its own configuration and reload modules at runtime.
"""

import importlib
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class SelfModification:
    """
    Provides safe, sandboxed self-modification capabilities:
    - Hot-reload of modules at runtime
    - Config patching
    - Plugin installation via pip
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.mods_dir = Path(self.config.get("mods_dir", "mods"))
        self._orchestrator = None  # injected by CoreOrchestrator

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        logger.info("SelfModification module ready.")

    def stop(self) -> None:
        logger.info("SelfModification module stopped.")

    def set_orchestrator(self, orchestrator) -> None:
        self._orchestrator = orchestrator

    # ------------------------------------------------------------------
    # Hot-reload
    # ------------------------------------------------------------------

    def reload_module(self, module_name: str) -> bool:
        """
        Hot-reload a Python module by name.
        Returns True on success, False on failure.
        """
        try:
            mod = sys.modules.get(module_name)
            if mod is None:
                logger.warning("Module '%s' is not loaded – nothing to reload.", module_name)
                return False
            importlib.reload(mod)
            logger.info("Module '%s' reloaded successfully.", module_name)
            return True
        except Exception as exc:
            logger.error("Failed to reload module '%s': %s", module_name, exc)
            return False

    # ------------------------------------------------------------------
    # Config patching
    # ------------------------------------------------------------------

    def patch_config(self, key: str, value: Any) -> None:
        """Update a config value at runtime and propagate to the orchestrator."""
        self.config[key] = value
        logger.info("Config patched: %s = %r", key, value)
        if self._orchestrator:
            self._orchestrator.config[key] = value

    # ------------------------------------------------------------------
    # Plugin installation
    # ------------------------------------------------------------------

    def install_plugin(self, package: str) -> bool:
        """
        Install a Python package at runtime using pip.
        SECURITY: Only call with trusted package names.
        """
        import subprocess  # noqa: PLC0415

        import re
        if not package or not re.fullmatch(r"[A-Za-z0-9_\-]+(?:\[.*?\])?(?:==[\w.]+)?", package):
            logger.error("Invalid package name rejected: %r", package)
            return False

        logger.info("Installing plugin: %s", package)
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pip", "install", "--quiet", package],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            logger.info("Plugin '%s' installed successfully.", package)
            return True
        logger.error("Plugin install failed for '%s': %s", package, result.stderr)
        return False
