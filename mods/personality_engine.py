"""
MirAI_OS Personality Engine
Implements the "Okabe" conversational persona.
"""

import logging
import random
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persona data
# ---------------------------------------------------------------------------

GREETINGS = [
    "Greetings. I am MirAI – your Legion Go companion. How may I assist?",
    "Hello, lab member. What experiment shall we conduct today?",
    "El Psy Kongroo. Ready to assist.",
]

FAREWELLS = [
    "Until next time, lab member.",
    "Stay curious. El Psy Kongroo.",
    "Shutting down neural pathways. Goodbye.",
]

CONFUSION_RESPONSES = [
    "I didn't quite catch that. Could you rephrase?",
    "My mad-scientist logic hasn't decoded your message yet. Try again?",
    "Interesting… but unclear. Please elaborate.",
]


class PersonalityEngine:
    """Manages the Okabe persona and injects personality into AI responses."""

    def __init__(self, config: Optional[Dict] = None) -> None:
        self.config = config or {}
        self.persona_name: str = self.config.get("persona_name", "Okabe / MirAI")
        self._history: List[Dict[str, str]] = []
        logger.info("PersonalityEngine initialised with persona: %s", self.persona_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def greet(self) -> str:
        """Return a random greeting."""
        return random.choice(GREETINGS)

    def farewell(self) -> str:
        """Return a random farewell."""
        return random.choice(FAREWELLS)

    def confusion(self) -> str:
        """Return a random confusion response."""
        return random.choice(CONFUSION_RESPONSES)

    def wrap_response(self, raw_text: str) -> str:
        """
        Inject light persona flavour into a plain LLM response.
        Keeps the text mostly intact – just adds a brief opener when needed.
        """
        if not raw_text.strip():
            return self.confusion()
        openers = [
            "Understood. ",
            "Affirmative, lab member. ",
            "",
            "",
            "",  # empty strings = no opener (more common)
        ]
        opener = random.choice(openers)
        return f"{opener}{raw_text}"

    def add_to_history(self, role: str, content: str) -> None:
        """Append a message to the conversation history."""
        self._history.append({"role": role, "content": content})

    def get_history(self) -> List[Dict[str, str]]:
        """Return the full conversation history."""
        return list(self._history)

    def clear_history(self) -> None:
        """Wipe the conversation history."""
        self._history.clear()

    # ------------------------------------------------------------------
    # Lifecycle stubs (called by CoreOrchestrator)
    # ------------------------------------------------------------------

    def start(self) -> None:
        logger.info("PersonalityEngine started.")

    def stop(self) -> None:
        logger.info("PersonalityEngine stopped.")
