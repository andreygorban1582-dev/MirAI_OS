"""
MirAI OS — Main Entry Point
Boots the Future Gadget Lab's AI operative.
"Reading Steiner, activated. El Psy Kongroo."
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import cfg

# ── Logging setup ─────────────────────────────────────────────────────────────
LOG_LEVEL = cfg.get("system", "log_level", default="INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/mirai.log", mode="a"),
    ],
)
logger = logging.getLogger("mirai")


BOOT_ART = r"""
 ███╗   ███╗██╗██████╗  █████╗ ██╗      ██████╗ ███████╗
 ████╗ ████║██║██╔══██╗██╔══██╗██║     ██╔═══██╗██╔════╝
 ██╔████╔██║██║██████╔╝███████║██║     ██║   ██║███████╗
 ██║╚██╔╝██║██║██╔══██╗██╔══██║██║     ██║   ██║╚════██║
 ██║ ╚═╝ ██║██║██║  ██║██║  ██║███████╗╚██████╔╝███████║
 ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝
                                                    OS v0.1.0
  Future Gadget Lab #8  |  Legion Go Node  |  El Psy Kongroo.
"""


async def startup_checks() -> bool:
    """Verify critical configuration before starting."""
    ok = True

    if not cfg.openrouter_keys:
        logger.error("No OpenRouter API keys found! Add them to .env")
        ok = False

    if not cfg.telegram_token or cfg.telegram_token == "YOUR_BOT_TOKEN_HERE":
        logger.error("TELEGRAM_BOT_TOKEN not set in .env!")
        ok = False

    if not cfg.telegram_admin_ids:
        logger.warning("TELEGRAM_ADMIN_IDS not set — bot will accept messages from anyone!")

    return ok


async def main() -> None:
    print(BOOT_ART)
    logger.info("MirAI OS booting...")

    # Ensure data directories exist
    for d in ["data/conversations", "data/vector_store", "data/capabilities", "data/sessions"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    # Copy .env from template if missing
    env_file = Path(".env")
    if not env_file.exists():
        template = Path("config/.env.example")
        if template.exists():
            import shutil
            shutil.copy(template, env_file)
            logger.warning(".env created from template. Edit it before continuing!")
            print("\n[!] Please edit .env with your API keys and run again.\n")
            sys.exit(1)

    # Startup checks
    if not await startup_checks():
        print("\n[!] Configuration errors found. Edit .env and try again.\n")
        print("Required:")
        print("  OPENROUTER_KEY_1=sk-or-v1-...")
        print("  TELEGRAM_BOT_TOKEN=...")
        sys.exit(1)

    logger.info(f"LLM: {cfg.llm.get('primary_model')} via OpenRouter ({len(cfg.openrouter_keys)} keys)")
    logger.info(f"Telegram: configured")
    logger.info(f"Nodes: {len(cfg.nodes)} configured ({len(cfg.active_nodes())} active)")

    # Start node heartbeat
    from network.node_manager import node_manager
    asyncio.create_task(node_manager.start_heartbeat(interval=30))
    logger.info("Node heartbeat started.")

    # Start Telegram bot (this blocks)
    logger.info("Starting Telegram bot...")
    from telegram.bot import run_bot
    await run_bot()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("MirAI OS shutting down. El Psy Kongroo.")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
