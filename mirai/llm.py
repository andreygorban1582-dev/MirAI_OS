"""
mirai/llm.py
────────────
LLM Engine – OpenRouter Integration
═════════════════════════════════════════════════════════════════════════════
What this module does
─────────────────────
• Wraps the OpenAI-compatible Python SDK pointed at OpenRouter's API endpoint.
• Sends a list of chat messages to the chosen model and streams the response.
• Automatically injects the system prompt defined in config.yaml.
• Counts tokens with tiktoken so the caller can enforce context-window limits.
• Falls back gracefully when the API is unreachable (returns an error string
  rather than crashing the whole agent).

Key classes / functions
───────────────────────
LLMEngine          – main class; call .chat(messages) for a response string.
count_tokens()     – utility: count tokens for a list of messages.
"""

from __future__ import annotations

import os
from typing import Generator, List

import tiktoken
from loguru import logger
from openai import OpenAI

from mirai.settings import settings


class LLMEngine:
    """
    Thin wrapper around the OpenRouter (OpenAI-compatible) API.

    Parameters
    ----------
    api_key : str, optional
        Override the key from settings/env.
    model : str, optional
        Override the model slug from settings.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.openrouter_api_key
        self._model = model or settings.openrouter_model
        self._base_url = settings.openrouter_base_url
        self._system_prompt = settings.llm_system_prompt
        self._temperature = settings.llm_temperature
        self._max_tokens = settings.llm_max_tokens

        if not self._api_key:
            logger.warning(
                "OPENROUTER_API_KEY is not set – LLM calls will fail until "
                "you add it to your .env file."
            )

        self._client = OpenAI(
            api_key=self._api_key or "NOT_SET",
            base_url=self._base_url,
        )

        # tiktoken encoding – fall back to cl100k_base for unknown models
        try:
            self._enc = tiktoken.encoding_for_model("gpt-4o")
        except KeyError:
            self._enc = tiktoken.get_encoding("cl100k_base")

    # ── Public API ────────────────────────────────────────────────────────────

    def chat(self, messages: List[dict]) -> str:
        """
        Send a conversation to the LLM and return the full reply as a string.

        The system prompt is prepended automatically; callers should pass only
        the user/assistant turns.

        Parameters
        ----------
        messages : list[dict]
            List of {"role": "user"|"assistant", "content": "..."} dicts.

        Returns
        -------
        str
            The assistant's reply text, or an error message starting with
            "[LLM Error]".
        """
        full_messages = [
            {"role": "system", "content": self._system_prompt},
            *messages,
        ]
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error(f"LLM request failed: {exc}")
            return f"[LLM Error] {exc}"

    def stream(self, messages: List[dict]) -> Generator[str, None, None]:
        """
        Same as chat() but yields text chunks as they arrive from the API.
        Useful for printing responses word-by-word in the terminal.
        """
        full_messages = [
            {"role": "system", "content": self._system_prompt},
            *messages,
        ]
        try:
            stream = self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            logger.error(f"LLM stream failed: {exc}")
            yield f"[LLM Error] {exc}"

    def count_tokens(self, messages: List[dict]) -> int:
        """Return the approximate token count for a list of messages."""
        total = 0
        for msg in messages:
            total += 4  # per-message overhead
            total += len(self._enc.encode(msg.get("content", "")))
        return total + 2  # reply overhead
