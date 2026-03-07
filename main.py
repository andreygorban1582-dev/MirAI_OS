#!/usr/bin/env python3
"""
main.py – MirAI_OS Entry Point
================================================================================
Integrates all components of MirAI_OS:
  - lab_personas.py  : 73 AI personas (Okabe, Rick, Geralt, Wrench, Kurisu…)
  - lab_edition.py   : Unified AI Agent Orchestrator with FastAPI REST API
  - mods.py          : Drop-in plugin/mod loader system

Run modes:
  python main.py --mode api    → Start FastAPI REST API server
  python main.py --mode cli    → Interactive CLI with persona selection
  python main.py --list-personas → Print all available personas

El Psy Kongroo.
"""

from __future__ import annotations

import asyncio
import logging
import sys

logger = logging.getLogger("MirAI_OS")

# ---------------------------------------------------------------------------
# Import personas
# ---------------------------------------------------------------------------
try:
    from lab_personas import ALL_PERSONAS, Persona
    _PERSONAS_AVAILABLE = True
    logger.info("Loaded %d personas from lab_personas.", len(ALL_PERSONAS))
except ImportError as exc:
    logger.warning("lab_personas not available: %s", exc)
    ALL_PERSONAS = {}
    _PERSONAS_AVAILABLE = False

# ---------------------------------------------------------------------------
# Import mod loader
# ---------------------------------------------------------------------------
try:
    from mods import get_default_loader, ModLoader
    _MODS_AVAILABLE = True
except ImportError as exc:
    logger.warning("mods not available: %s", exc)
    _MODS_AVAILABLE = False

# ---------------------------------------------------------------------------
# Import lab_edition orchestrator and FastAPI app
# ---------------------------------------------------------------------------
try:
    from lab_edition import Orchestrator, app as _fastapi_app, config as lab_config
    import uvicorn
    _LAB_EDITION_AVAILABLE = True
except ImportError as exc:
    logger.warning(
        "lab_edition not available (missing deps): %s\n"
        "Run: pip install fastapi uvicorn httpx python-dotenv",
        exc,
    )
    _LAB_EDITION_AVAILABLE = False


def _build_orchestrator_with_personas() -> "Orchestrator | None":
    """Create an Orchestrator and register persona-based agents."""
    if not _LAB_EDITION_AVAILABLE:
        return None

    orchestrator = Orchestrator()

    if _PERSONAS_AVAILABLE:
        # Register each persona as a named agent in the orchestrator
        for name, persona in ALL_PERSONAS.items():
            orchestrator.create_agent(name, system_prompt=persona.system_prompt)
        logger.info(
            "Registered %d persona-based agents in orchestrator.", len(ALL_PERSONAS)
        )

    return orchestrator


def _init_mod_loader() -> "ModLoader | None":
    """Initialise the mod loader and load mods/ directory if it exists."""
    if not _MODS_AVAILABLE:
        return None

    loader = get_default_loader()
    loader.load_directory("mods/")
    loader.initialise(bot=None, llm=None, ctx={})
    logger.info("Mod loader ready. Mods loaded: %s", [m.name for m in loader.mods])
    return loader


async def _run_cli(orchestrator: "Orchestrator", mod_loader: "ModLoader | None") -> None:
    """Interactive CLI mode with persona selection and mod pipeline."""
    await orchestrator.initialize()

    print("\n=== MirAI_OS – The Lab Edition ===")
    if _PERSONAS_AVAILABLE:
        print(f"Personas available: {sorted(ALL_PERSONAS.keys())}")
    print("Type 'exit' to quit, 'personas' to list personas.\n")

    active_persona: str | None = None

    while True:
        try:
            prompt = f"[{active_persona or 'default'}] > "
            user_input = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye. El Psy Kongroo.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye. El Psy Kongroo.")
            break

        if user_input.lower() == "personas":
            for p_name in sorted(ALL_PERSONAS.keys()):
                print(f"  - {p_name}")
            continue

        if user_input.lower().startswith("persona "):
            requested = user_input[8:].strip()
            if requested in ALL_PERSONAS:
                active_persona = requested
                print(f"Switched to persona: {active_persona}")
            else:
                print(f"Unknown persona '{requested}'. Use 'personas' to list.")
            continue

        # Route message through mod pipeline first
        reply: str | None = None
        if mod_loader is not None:
            reply = mod_loader.dispatch_message(user_input, ctx={})

        if reply is not None:
            print(f"\n{reply}\n")
            continue

        # Submit task to the orchestrator (uses active persona agent if set)
        agent_name = active_persona or "default"
        try:
            task_id = await orchestrator.submit_task(user_input, agent_name)
            # Poll briefly for result
            for _ in range(10):
                await asyncio.sleep(0.5)
                result = orchestrator.get_result(task_id)
                if result:
                    output = result.get("result") or result.get("output") or str(result)
                    print(f"\n{output}\n")
                    break
            else:
                print(f"(Task {task_id} is still processing…)\n")
        except Exception as exc:
            print(f"Error: {exc}\n")


def _list_personas() -> None:
    """Print all available personas to stdout."""
    if not _PERSONAS_AVAILABLE:
        print("Personas module not available.")
        return
    print(f"Available personas ({len(ALL_PERSONAS)}):")
    for name in sorted(ALL_PERSONAS.keys()):
        persona = ALL_PERSONAS[name]
        snippet = persona.system_prompt[:80].replace("\n", " ")
        print(f"  {name:<30} {snippet}…")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="MirAI_OS – Unified AI Agent Orchestrator"
    )
    parser.add_argument(
        "--mode",
        choices=["api", "cli"],
        default="cli",
        help="Run mode: FastAPI REST server (api) or interactive CLI (cli). Default: cli",
    )
    parser.add_argument("--host", default="0.0.0.0", help="API host (api mode)")
    parser.add_argument("--port", type=int, default=8000, help="API port (api mode)")
    parser.add_argument(
        "--list-personas", action="store_true", help="List all available personas and exit"
    )
    args = parser.parse_args()

    if args.list_personas:
        _list_personas()
        return

    # Initialise mod loader (always, independent of mode)
    mod_loader = _init_mod_loader()

    if args.mode == "api":
        if not _LAB_EDITION_AVAILABLE:
            print(
                "ERROR: lab_edition dependencies are missing.\n"
                "Run: pip install fastapi uvicorn httpx python-dotenv",
                file=sys.stderr,
            )
            sys.exit(1)
        logger.info("Starting FastAPI server on %s:%s", args.host, args.port)
        uvicorn.run(_fastapi_app, host=args.host, port=args.port)

    else:  # cli
        if not _LAB_EDITION_AVAILABLE:
            print(
                "WARNING: lab_edition unavailable – running in persona-listing mode only."
            )
            _list_personas()
            return

        orchestrator = _build_orchestrator_with_personas()
        if orchestrator is None:
            print("ERROR: Could not initialize orchestrator.", file=sys.stderr)
            sys.exit(1)
        asyncio.run(_run_cli(orchestrator, mod_loader))


if __name__ == "__main__":
    main()
