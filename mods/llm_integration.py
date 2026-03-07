"""
MirAI_OS LLM Integration
Connects to a local or remote language model.
Supports OpenAI-compatible APIs (e.g. LM Studio, Ollama, OpenAI).
"""

import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class LLMIntegration:
    """Wrapper around an LLM provider with conversation memory."""

    DEFAULT_SYSTEM_PROMPT = (
        "You are MirAI, an advanced AI assistant running on a Lenovo Legion Go. "
        "You are helpful, concise, and slightly eccentric in the style of Okabe Rintaro. "
        "Always prioritise accuracy and brevity."
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.provider: str = self.config.get("llm_provider", "openai_compatible")
        self.base_url: str = self.config.get("llm_base_url", "http://localhost:1234/v1")
        self.api_key: str = self.config.get("llm_api_key", "not-needed")
        self.model: str = self.config.get("llm_model", "local-model")
        self.system_prompt: str = self.config.get(
            "llm_system_prompt", self.DEFAULT_SYSTEM_PROMPT
        )
        self._client: Any = None
        self._history: List[Dict[str, str]] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        try:
            from openai import OpenAI  # type: ignore

            self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)
            logger.info(
                "LLMIntegration connected to %s (model: %s)", self.base_url, self.model
            )
        except ImportError:
            logger.warning(
                "openai package not installed – LLM features will be limited. "
                "Run: pip install openai"
            )

    def stop(self) -> None:
        self._client = None
        logger.info("LLMIntegration stopped.")

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate a response for *prompt*, maintaining conversation history."""
        if self._client is None:
            return "[LLM not connected – check your configuration]"

        self._history.append({"role": "user", "content": prompt})
        messages = [{"role": "system", "content": self.system_prompt}] + self._history

        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            )
            reply = completion.choices[0].message.content or ""
            self._history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as exc:
            logger.error("LLM generation error: %s", exc)
            return f"[LLM error: {exc}]"

    def clear_history(self) -> None:
        """Reset conversation history."""
        self._history.clear()
