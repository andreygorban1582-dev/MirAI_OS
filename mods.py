"""
MirAI_OS  –  Mod Loader  (Mod 2)
Drop-in Python extensions with full lifecycle hooks.

Usage:
    loader = ModLoader()
    loader.load_file("my_mod.py")           # single file
    loader.load_directory("mods/")          # whole directory

Mod API:
    MOD_NAME    = "my_skill"   # required
    MOD_VERSION = "1.0.0"      # optional

    def setup(bot, llm, ctx):          ...
    def on_message(message, ctx):      return str | None
    def on_startup(ctx):               ...   # Mod 2
    def on_shutdown(ctx):              ...   # Mod 2
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import logging
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("mirai.mods")


# ═══════════════════════════════════════════════════════════════════════════════
# Mod  –  wraps one loaded Python module
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Mod:
    """Represents a single loaded mod."""

    name:    str
    version: str
    module:  types.ModuleType

    # ── Lifecycle hooks ───────────────────────────────────────────────────────

    async def setup(self, bot: Any, llm: Any, ctx: dict) -> None:
        """Called once when the mod is loaded."""
        await self._call("setup", bot, llm, ctx)

    async def on_message(self, message: str, ctx: dict) -> Optional[str]:
        """
        Called for every incoming message.
        Return a string to intercept the message; return None to pass through.
        """
        if hasattr(self.module, "on_message"):
            try:
                result = self.module.on_message(message, ctx)
                return await result if asyncio.iscoroutine(result) else result
            except Exception as exc:
                logger.error("[mod:%s] on_message error: %s", self.name, exc)
        return None

    # ── Mod 2 hooks ───────────────────────────────────────────────────────────

    async def on_startup(self, ctx: dict) -> None:
        """Called once when the application starts up."""
        await self._call("on_startup", ctx)

    async def on_shutdown(self, ctx: dict) -> None:
        """Called once when the application shuts down."""
        await self._call("on_shutdown", ctx)

    async def on_tool_call(self, tool: str, args: dict, ctx: dict) -> Optional[str]:
        """Mod 2: Called when an agent tool is invoked."""
        if hasattr(self.module, "on_tool_call"):
            try:
                result = self.module.on_tool_call(tool, args, ctx)
                return await result if asyncio.iscoroutine(result) else result
            except Exception as exc:
                logger.error("[mod:%s] on_tool_call error: %s", self.name, exc)
        return None

    async def on_persona_switch(self, from_p: str, to_p: str, ctx: dict) -> None:
        """Mod 2: Called when the active persona changes."""
        await self._call("on_persona_switch", from_p, to_p, ctx)

    # ── Helper ────────────────────────────────────────────────────────────────

    async def _call(self, hook: str, *args: Any) -> None:
        if hasattr(self.module, hook):
            try:
                result = getattr(self.module, hook)(*args)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.error("[mod:%s] %s error: %s", self.name, hook, exc)

    def __repr__(self) -> str:
        return f"<Mod name={self.name!r} version={self.version!r}>"


# ═══════════════════════════════════════════════════════════════════════════════
# ModLoader  –  discovers, loads, and manages mods
# ═══════════════════════════════════════════════════════════════════════════════

class ModLoader:
    """Discovers, loads, and hot-reloads Python mods."""

    def __init__(self) -> None:
        self._mods: dict[str, Mod] = {}

    # ── Loading ───────────────────────────────────────────────────────────────

    def load_file(self, path: str | Path) -> Optional[Mod]:
        """Load a single mod from a Python file."""
        path = Path(path)
        if not path.exists():
            logger.warning("[ModLoader] file not found: %s", path)
            return None

        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            logger.error("[ModLoader] cannot create spec for: %s", path)
            return None

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        except Exception as exc:
            logger.error("[ModLoader] exec failed for %s: %s", path, exc)
            return None

        mod = Mod(
            name    = getattr(module, "MOD_NAME",    path.stem),
            version = getattr(module, "MOD_VERSION", "0.0.0"),
            module  = module,
        )
        self._mods[mod.name] = mod
        logger.info("[ModLoader] loaded '%s' v%s", mod.name, mod.version)
        return mod

    def load_directory(self, directory: str | Path) -> list[Mod]:
        """Load all *.py files in a directory as mods."""
        directory = Path(directory)
        if not directory.is_dir():
            logger.warning("[ModLoader] directory not found: %s", directory)
            return []
        loaded: list[Mod] = []
        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            mod = self.load_file(py_file)
            if mod:
                loaded.append(mod)
        logger.info("[ModLoader] loaded %d mod(s) from %s", len(loaded), directory)
        return loaded

    # ── Mod 2: hot-reload ─────────────────────────────────────────────────────

    def reload(self, mod_name: str) -> bool:
        """Hot-reload a mod by name without restarting the application."""
        mod = self._mods.get(mod_name)
        if mod is None:
            logger.warning("[ModLoader] mod not found for reload: %s", mod_name)
            return False
        try:
            importlib.reload(mod.module)
            logger.info("[ModLoader] reloaded '%s'", mod_name)
            return True
        except Exception as exc:
            logger.error("[ModLoader] reload failed for '%s': %s", mod_name, exc)
            return False

    def unload(self, mod_name: str) -> bool:
        """Remove a mod from the loader."""
        if mod_name in self._mods:
            del self._mods[mod_name]
            logger.info("[ModLoader] unloaded '%s'", mod_name)
            return True
        return False

    # ── Dispatching ───────────────────────────────────────────────────────────

    async def dispatch_message(self, message: str, ctx: dict) -> Optional[str]:
        """Dispatch a message through all mods; return first non-None reply."""
        for mod in self.mods:
            result = await mod.on_message(message, ctx)
            if result is not None:
                return result
        return None

    async def dispatch_tool_call(
        self, tool: str, args: dict, ctx: dict
    ) -> Optional[str]:
        """Mod 2: Dispatch a tool call through all mods."""
        for mod in self.mods:
            result = await mod.on_tool_call(tool, args, ctx)
            if result is not None:
                return result
        return None

    async def startup_all(self, ctx: dict) -> None:
        """Mod 2: Run on_startup for all loaded mods."""
        for mod in self.mods:
            await mod.on_startup(ctx)

    async def shutdown_all(self, ctx: dict) -> None:
        """Mod 2: Run on_shutdown for all loaded mods."""
        for mod in self.mods:
            await mod.on_shutdown(ctx)

    async def notify_persona_switch(
        self, from_p: str, to_p: str, ctx: dict
    ) -> None:
        """Mod 2: Notify all mods of a persona change."""
        for mod in self.mods:
            await mod.on_persona_switch(from_p, to_p, ctx)

    # ── Introspection ─────────────────────────────────────────────────────────

    @property
    def mods(self) -> list[Mod]:
        return list(self._mods.values())

    def get(self, mod_name: str) -> Optional[Mod]:
        return self._mods.get(mod_name)

    def __len__(self) -> int:
        return len(self._mods)

    def __repr__(self) -> str:
        names = ", ".join(self._mods)
        return f"<ModLoader mods=[{names}]>"
