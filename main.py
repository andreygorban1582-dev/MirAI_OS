"""
MirAI_OS – Main entry point
Combines core modules + Mod 2 into a single unified application.
Supports CLI interactive mode and background service mode.

Usage:
    python main.py [--mode cli|service|telegram]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
from pathlib import Path

# ── bootstrap: ensure project root is on sys.path ─────────────────────────────
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── load .env if present (before importing config) ────────────────────────────
_env_path = _ROOT / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _, _val = _line.partition("=")
            os.environ.setdefault(_key.strip(), _val.strip())

import config  # noqa: E402  (after env loading)

# ── directories ───────────────────────────────────────────────────────────────
Path(config.DATA_DIR).mkdir(parents=True, exist_ok=True)
Path(config.LOG_DIR).mkdir(parents=True, exist_ok=True)

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(config.LOG_DIR) / "mirai.log"),
    ],
)
logger = logging.getLogger("mirai")

# ── module imports ────────────────────────────────────────────────────────────
from modules.llm_engine import LLMEngine
from modules.agent_flows import AgentFlows
from modules.context_optimizer import ContextOptimizer
from modules.self_modification import SelfModification
from modules.kali_integration import KaliIntegration
from modules.ssh_connector import SSHConnector
from modules.voice_io import VoiceIO

# ── mod2 imports ─────────────────────────────────────────────────────────────
if config.MOD2_ENABLED:
    from mod2.memory_system import MemorySystem
    from mod2.web_scraper import WebScraper
    from mod2.advanced_agent import AdvancedAgent


def build_system() -> dict:
    """Initialise and wire all MirAI_OS components. Returns a component dict."""
    logger.info("Initialising MirAI_OS v%s…", config.APP_VERSION)

    llm = LLMEngine()
    context = ContextOptimizer(llm)
    agent = AgentFlows(llm)
    self_mod = SelfModification()
    kali = KaliIntegration()
    ssh = SSHConnector()
    voice = VoiceIO()

    components: dict = {
        "llm": llm,
        "context": context,
        "agent": agent,
        "self_mod": self_mod,
        "kali": kali,
        "ssh": ssh,
        "voice": voice,
    }

    if config.MOD2_ENABLED:
        memory = MemorySystem()
        scraper = WebScraper()
        adv_agent = AdvancedAgent(llm, memory=memory, scraper=scraper)
        components.update({
            "memory": memory,
            "scraper": scraper,
            "adv_agent": adv_agent,
        })
        logger.info("Mod 2 loaded: memory=%s, web_search=%s",
                    config.MOD2_MEMORY_PATH, config.MOD2_WEB_SEARCH)

    logger.info("MirAI_OS ready. LLM backend: %s", llm.backend)
    return components


# ── CLI interactive loop ──────────────────────────────────────────────────────

def run_cli(components: dict) -> None:
    """Interactive CLI chat with MirAI_OS (Okabe personality)."""
    llm: LLMEngine = components["llm"]
    context: ContextOptimizer = components["context"]
    adv_agent = components.get("adv_agent")
    agent: AgentFlows = components["agent"]

    print(f"\n{'='*60}")
    print(f"  {config.APP_NAME} v{config.APP_VERSION} – Interactive CLI")
    print(f"  LLM: {llm.backend}  |  Mod2: {config.MOD2_ENABLED}")
    print(f"{'='*60}")
    print("  Commands: /reset /status /mod2 /agent <task> /quit")
    print(f"{'='*60}\n")
    print("El Psy Kongroo! I am Hououin Kyouma. How can I assist you, lab member?\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nFarewell, lab member. El Psy Kongroo.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "/q"):
            print("Farewell. El Psy Kongroo.")
            break

        if user_input.lower() == "/reset":
            context.clear()
            print("Mirai: Memory purged. A new experiment begins.\n")
            continue

        if user_input.lower() == "/status":
            status = components["self_mod"].get_status()
            for k, v in status.items():
                print(f"  {k}: {v}")
            print()
            continue

        if user_input.lower() == "/mod2":
            if adv_agent:
                print("Mirai: Mod 2 is ACTIVE! Advanced capabilities online.")
            else:
                print("Mirai: Mod 2 is disabled. Set MOD2_ENABLED=true to enable.")
            print()
            continue

        if user_input.lower().startswith("/agent "):
            task = user_input[7:].strip()
            runner = adv_agent if adv_agent else agent
            print("Mirai: Running agent task…")
            result = runner.run(task)
            print(f"Mirai: {result}\n")
            continue

        # Standard LLM chat
        context.add("user", user_input)
        reply = llm.chat(user_input, history=context.get_history())
        context.add("assistant", reply)
        print(f"Mirai: {reply}\n")


# ── service mode ─────────────────────────────────────────────────────────────

def run_service(components: dict) -> None:
    """Run all background services (Telegram, voice)."""
    threads: list[threading.Thread] = []

    # Telegram bot
    if config.TELEGRAM_BOT_TOKEN:
        from modules.telegram_bot import TelegramBot
        bot = TelegramBot(components["llm"])
        t = threading.Thread(target=bot.start, daemon=True, name="telegram-bot")
        t.start()
        threads.append(t)
        logger.info("Telegram bot thread started.")
    else:
        logger.warning("Telegram bot token not configured.")

    # Voice I/O
    if config.VOICE_ENABLED:
        voice: VoiceIO = components["voice"]
        llm: LLMEngine = components["llm"]
        context: ContextOptimizer = components["context"]

        def on_speech(text: str) -> None:
            logger.info("Voice input: %s", text)
            reply = llm.chat(text, history=context.get_history())
            context.add("user", text)
            context.add("assistant", reply)
            voice.speak(reply)

        voice.start(on_speech)

    if not threads:
        logger.warning("No services started. Configure TELEGRAM_BOT_TOKEN or VOICE_ENABLED.")
        return

    logger.info("MirAI_OS service running. Press Ctrl+C to stop.")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logger.info("Service stopped.")


# ── Telegram mode ─────────────────────────────────────────────────────────────

def run_telegram(components: dict) -> None:
    """Run Telegram bot in the foreground."""
    from modules.telegram_bot import TelegramBot
    if not config.TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set in environment or .env file.")
        sys.exit(1)
    bot = TelegramBot(components["llm"])
    bot.start()


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"{config.APP_NAME} v{config.APP_VERSION}"
    )
    parser.add_argument(
        "--mode",
        choices=["cli", "service", "telegram"],
        default="cli",
        help="Launch mode (default: cli)",
    )
    args = parser.parse_args()

    components = build_system()

    if args.mode == "cli":
        run_cli(components)
    elif args.mode == "service":
        run_service(components)
    elif args.mode == "telegram":
        run_telegram(components)


if __name__ == "__main__":
    main()
