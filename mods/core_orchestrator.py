"""
MirAI_OS Core Orchestrator
Manages all modules and routes requests between them.
Optimised for the Lenovo Legion Go (Windows 11, AMD Ryzen Z1 Extreme).
"""

import logging
import threading
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger(__name__)


class CoreOrchestrator:
    """Central hub that coordinates all MirAI_OS modules."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self._modules: Dict[str, Any] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        logger.info("CoreOrchestrator initialised.")

    # ------------------------------------------------------------------
    # Module registration
    # ------------------------------------------------------------------

    def register_module(self, name: str, module: Any) -> None:
        """Register a module by name so other parts of the system can find it."""
        with self._lock:
            self._modules[name] = module
            logger.info("Module registered: %s", name)

    def get_module(self, name: str) -> Optional[Any]:
        """Return a previously registered module, or None."""
        return self._modules.get(name)

    # ------------------------------------------------------------------
    # Event / hook system
    # ------------------------------------------------------------------

    def on(self, event: str, callback: Callable) -> None:
        """Subscribe *callback* to *event*."""
        self._hooks.setdefault(event, []).append(callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Emit *event*, calling all registered callbacks."""
        for cb in self._hooks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception as exc:
                logger.error("Hook error for event '%s': %s", event, exc)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start all registered modules."""
        logger.info("Starting all modules…")
        for name, mod in self._modules.items():
            start_fn = getattr(mod, "start", None)
            if callable(start_fn):
                try:
                    start_fn()
                    logger.info("Started: %s", name)
                except Exception as exc:
                    logger.error("Failed to start %s: %s", name, exc)
        self.emit("system_ready")

    def stop(self) -> None:
        """Gracefully stop all registered modules."""
        logger.info("Stopping all modules…")
        for name, mod in reversed(list(self._modules.items())):
            stop_fn = getattr(mod, "stop", None)
            if callable(stop_fn):
                try:
                    stop_fn()
                    logger.info("Stopped: %s", name)
                except Exception as exc:
                    logger.error("Failed to stop %s: %s", name, exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def process(self, user_input: str) -> str:
        """Route *user_input* through the LLM and return the AI response."""
        llm = self.get_module("llm")
        if llm is None:
            return "LLM module not available."
        return llm.generate(user_input)
