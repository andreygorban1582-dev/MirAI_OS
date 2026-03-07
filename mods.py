"""
mods.py – MirAI_OS Mod Loader
=================================
Drop custom modules here (or register them via the API below) to extend
the AI's capabilities without touching main.py.

HOW TO ADD A MOD
----------------
1. Create a Python file anywhere on disk (e.g. my_skill.py):

    # my_skill.py
    MOD_NAME    = "my_skill"
    MOD_VERSION = "1.0.0"

    def setup(bot, llm, ctx):
        \"\"\"Called once when the mod is loaded.  Receives the live
        MirAI_OS subsystem references so you can hook into them.\"\"\"
        print(f"[{MOD_NAME}] loaded!")

    def on_message(message: str, ctx: dict) -> str | None:
        \"\"\"Optional: intercept every incoming message.
        Return a string to short-circuit the default pipeline,
        or None to let normal processing continue.\"\"\"
        return None

2. Register it at startup:
        from mods import ModLoader
        loader = ModLoader()
        loader.load_file("my_skill.py")

   OR drop the file into the mods/ sub-directory and call:
        loader.load_directory("mods/")

That's it – the mod is now live.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("MirAI_OS.mods")


# ---------------------------------------------------------------------------
# Mod descriptor
# ---------------------------------------------------------------------------

class Mod:
    """Wraps a loaded mod module and exposes its lifecycle hooks."""

    def __init__(self, module: Any) -> None:
        self.module = module
        self.name: str = getattr(module, "MOD_NAME", module.__name__)
        self.version: str = getattr(module, "MOD_VERSION", "0.0.0")
        self._setup: Callable | None = getattr(module, "setup", None)
        self._on_message: Callable | None = getattr(module, "on_message", None)

    # ------------------------------------------------------------------
    def setup(self, bot: Any, llm: Any, ctx: dict) -> None:
        if self._setup:
            try:
                self._setup(bot, llm, ctx)
                logger.info("Mod '%s' v%s initialised.", self.name, self.version)
            except Exception as exc:  # noqa: BLE001
                logger.error("Mod '%s' setup failed: %s", self.name, exc)

    def on_message(self, message: str, ctx: dict) -> str | None:
        """Return a reply string to override the default LLM reply, or None."""
        if self._on_message:
            try:
                return self._on_message(message, ctx)
            except Exception as exc:  # noqa: BLE001
                logger.error("Mod '%s' on_message failed: %s", self.name, exc)
        return None

    def __repr__(self) -> str:
        return f"<Mod name={self.name!r} version={self.version!r}>"


# ---------------------------------------------------------------------------
# Mod loader
# ---------------------------------------------------------------------------

class ModLoader:
    """
    Discovers, loads, and manages MirAI_OS mods.

    Usage::

        loader = ModLoader()
        loader.load_directory("mods/")        # load every .py in a folder
        loader.load_file("path/to/my_mod.py") # load a single file

        # After all subsystems are ready, call initialise() once:
        loader.initialise(bot=bot, llm=llm_engine, ctx=shared_context)

        # To route a message through all mods before the LLM:
        reply = loader.dispatch_message("hello", ctx=shared_context)
        if reply is None:
            reply = llm_engine.chat("hello")
    """

    def __init__(self) -> None:
        self._mods: list[Mod] = []

    # ------------------------------------------------------------------
    # Loading helpers
    # ------------------------------------------------------------------

    def load_file(self, path: str | Path) -> Mod | None:
        """Load a single mod from a .py file and register it."""
        path = Path(path).resolve()
        if not path.exists():
            logger.error("Mod file not found: %s", path)
            return None

        module_name = f"_mirai_mod_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            logger.error("Cannot create module spec for: %s", path)
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            logger.error("Error executing mod file %s: %s", path, exc)
            return None

        mod = Mod(module)
        self._mods.append(mod)
        logger.info("Loaded mod '%s' from %s", mod.name, path)
        return mod

    def load_directory(self, directory: str | Path) -> list[Mod]:
        """Load all .py files inside *directory* as mods."""
        directory = Path(directory)
        if not directory.is_dir():
            logger.warning("Mod directory not found: %s", directory)
            return []

        loaded: list[Mod] = []
        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue  # skip __init__.py etc.
            mod = self.load_file(py_file)
            if mod:
                loaded.append(mod)
        return loaded

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialise(self, bot: Any = None, llm: Any = None, ctx: dict | None = None) -> None:
        """Call setup() on every registered mod."""
        ctx = ctx or {}
        for mod in self._mods:
            mod.setup(bot, llm, ctx)

    # ------------------------------------------------------------------
    # Message pipeline
    # ------------------------------------------------------------------

    def dispatch_message(self, message: str, ctx: dict | None = None) -> str | None:
        """
        Pass *message* through every mod's on_message hook in load order.
        The first non-None return value wins and short-circuits the pipeline.
        Returns None if no mod handled the message.
        """
        ctx = ctx or {}
        for mod in self._mods:
            result = mod.on_message(message, ctx)
            if result is not None:
                logger.debug("Mod '%s' handled message.", mod.name)
                return result
        return None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add_mod(self, mod: Mod) -> None:
        """Register a pre-constructed :class:`Mod` instance."""
        self._mods.append(mod)
        logger.info("Registered mod '%s' v%s", mod.name, mod.version)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def mods(self) -> list[Mod]:
        """Read-only list of loaded mods."""
        return list(self._mods)

    def list_mods(self) -> None:
        """Print a summary of all loaded mods to stdout."""
        if not self._mods:
            print("No mods loaded.")
            return
        print(f"{'Name':<25} {'Version':<10} Module")
        print("-" * 55)
        for mod in self._mods:
            print(f"{mod.name:<25} {mod.version:<10} {mod.module.__name__}")


# ---------------------------------------------------------------------------
# Example / built-in stub mods  (remove or replace as desired)
# ---------------------------------------------------------------------------

class _EchoMod:
    """Built-in stub: echoes messages that start with '!echo '."""
    MOD_NAME = "echo"
    MOD_VERSION = "1.0.0"

    @staticmethod
    def setup(bot, llm, ctx):
        pass  # nothing to initialise

    @staticmethod
    def on_message(message: str, ctx: dict) -> str | None:
        if message.lower().startswith("!echo "):
            return message[6:]
        return None


# Register the built-in echo mod so there is always at least one example.
_BUILTIN_ECHO_MOD = Mod(_EchoMod)


def get_default_loader() -> ModLoader:
    """Return a ModLoader pre-loaded with the built-in mods."""
    loader = ModLoader()
    loader.add_mod(_BUILTIN_ECHO_MOD)
    return loader
