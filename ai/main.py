"""
MirAI_OS – Main AI application
Entry point that wires all mods together.
"""

import logging
import os
import sys
from pathlib import Path

# Ensure the project root is on the path when run directly
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.config import load_config  # noqa: E402
from mods.core_orchestrator import CoreOrchestrator  # noqa: E402
from mods.llm_integration import LLMIntegration  # noqa: E402
from mods.personality_engine import PersonalityEngine  # noqa: E402
from mods.self_modification import SelfModification  # noqa: E402
from mods.telegram_bot import TelegramBot  # noqa: E402
from mods.voice_system import VoiceSystem  # noqa: E402


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                Path(os.getenv("APPDATA", ".")) / "MirAI_OS" / "mirai.log",
                encoding="utf-8",
                delay=True,
            ),
        ],
    )


def build_system(cfg: dict) -> CoreOrchestrator:
    """Construct and register all modules."""
    orchestrator = CoreOrchestrator(cfg)

    personality = PersonalityEngine(cfg)
    llm = LLMIntegration(cfg)
    voice = VoiceSystem(cfg)
    telegram = TelegramBot(cfg)
    self_mod = SelfModification(cfg)
    self_mod.set_orchestrator(orchestrator)

    # Wire Telegram to the LLM
    telegram.set_process_function(orchestrator.process)

    # Wire voice transcript to the orchestrator
    voice.on_transcript(
        lambda text: print(f"[Voice → AI] {orchestrator.process(text)}")
    )

    orchestrator.register_module("personality", personality)
    orchestrator.register_module("llm", llm)
    orchestrator.register_module("voice", voice)
    orchestrator.register_module("telegram", telegram)
    orchestrator.register_module("self_mod", self_mod)

    return orchestrator


def run_interactive(orchestrator: CoreOrchestrator) -> None:
    """Simple REPL for text-based interaction."""
    personality: PersonalityEngine = orchestrator.get_module("personality")
    print(personality.greet() if personality else "MirAI ready.")
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.lower() in {"quit", "exit", "q"}:
            break
        if not user_input:
            continue
        response = orchestrator.process(user_input)
        if personality:
            response = personality.wrap_response(response)
        print(f"MirAI: {response}\n")

    if personality:
        print(personality.farewell())


def main() -> None:
    cfg = load_config()
    setup_logging(cfg.get("log_level", "INFO"))
    logger = logging.getLogger(__name__)

    # Ensure log directory exists
    log_dir = Path(os.getenv("APPDATA", ".")) / "MirAI_OS"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.info("MirAI_OS starting on Legion Go…")
    orchestrator = build_system(cfg)

    try:
        orchestrator.start()
        run_interactive(orchestrator)
    except Exception as exc:
        logger.error("Fatal error: %s", exc, exc_info=True)
    finally:
        orchestrator.stop()
        logger.info("MirAI_OS shut down cleanly.")


if __name__ == "__main__":
    main()
