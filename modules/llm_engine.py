"""
LLM Engine – priority: Ollama → Transformers → OpenRouter.
Provides a unified chat/completion interface for MirAI_OS.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

import config

logger = logging.getLogger(__name__)


class LLMEngine:
    """Unified LLM client that falls back across backends automatically."""

    def __init__(self) -> None:
        self.backend: str = self._detect_backend()
        logger.info("LLMEngine: using backend '%s'", self.backend)

    # ── backend detection ─────────────────────────────────────────────────────

    def _detect_backend(self) -> str:
        if self._ollama_available():
            return "ollama"
        try:
            import transformers  # noqa: F401
            return "transformers"
        except ImportError:
            pass
        if config.OPENROUTER_API_KEY:
            return "openrouter"
        return "stub"

    def _ollama_available(self) -> bool:
        try:
            url = f"{config.OLLAMA_URL}/api/tags"
            with urllib.request.urlopen(url, timeout=3) as resp:  # noqa: S310
                return resp.status == 200
        except Exception:
            return False

    # ── public API ────────────────────────────────────────────────────────────

    def chat(
        self,
        prompt: str,
        system: str = config.OKABE_SYSTEM_PROMPT,
        history: Optional[list] = None,
        temperature: float = 0.7,
    ) -> str:
        """Return the assistant reply as a plain string."""
        if self.backend == "ollama":
            return self._ollama_chat(prompt, system, history, temperature)
        if self.backend == "transformers":
            return self._transformers_chat(prompt, system, history)
        if self.backend == "openrouter":
            return self._openrouter_chat(prompt, system, history, temperature)
        return (
            "El Psy Kongroo… My systems are offline, lab member. "
            "No LLM backend is available."
        )

    # ── Ollama ────────────────────────────────────────────────────────────────

    def _ollama_chat(
        self,
        prompt: str,
        system: str,
        history: Optional[list],
        temperature: float,
    ) -> str:
        messages = self._build_messages(system, history, prompt)
        payload = json.dumps(
            {
                "model": config.OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            }
        ).encode()
        req = urllib.request.Request(
            f"{config.OLLAMA_URL}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
                data = json.loads(resp.read())
                return data["message"]["content"].strip()
        except Exception as exc:
            logger.error("Ollama error: %s", exc)
            return f"[Ollama error: {exc}]"

    # ── Transformers ──────────────────────────────────────────────────────────

    def _transformers_chat(
        self,
        prompt: str,
        system: str,
        history: Optional[list],
    ) -> str:
        try:
            from transformers import pipeline  # type: ignore

            combined = f"{system}\n\n{prompt}"
            pipe = pipeline("text-generation", model="gpt2", max_new_tokens=200)
            result = pipe(combined)
            return result[0]["generated_text"][len(combined):].strip()
        except Exception as exc:
            logger.error("Transformers error: %s", exc)
            return f"[Transformers error: {exc}]"

    # ── OpenRouter ────────────────────────────────────────────────────────────

    def _openrouter_chat(
        self,
        prompt: str,
        system: str,
        history: Optional[list],
        temperature: float,
    ) -> str:
        messages = self._build_messages(system, history, prompt)
        payload = json.dumps(
            {
                "model": config.OPENROUTER_MODEL,
                "messages": messages,
                "temperature": temperature,
            }
        ).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/andreygorban1582-dev/MirAI_OS",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.error("OpenRouter error: %s", exc)
            return f"[OpenRouter error: {exc}]"

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_messages(
        system: str, history: Optional[list], prompt: str
    ) -> list:
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return messages
