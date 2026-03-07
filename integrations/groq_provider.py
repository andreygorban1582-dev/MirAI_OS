"""
MirAI OS — Groq Integration (Optional)
Groq offers the FASTEST free LLM inference available.
Models: Llama 3.1 70B, Mixtral 8x7B, Gemma 2 9B
Free tier: 14,400 requests/day (6000 tokens/min)

Enable: set GROQ_API_KEY in .env
        set integrations.groq.enabled: true in settings.yaml
"""
from __future__ import annotations

import logging
import os
from typing import Optional, AsyncIterator

logger = logging.getLogger("mirai.integrations.groq")

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODELS = {
    "fast": "llama-3.1-8b-instant",         # Fastest — simple queries
    "balanced": "llama-3.1-70b-versatile",  # Best free model — complex tasks
    "code": "llama3-70b-8192",              # Good for code
    "mix": "mixtral-8x7b-32768",            # Long context (32k)
}


class GroqProvider:
    """Groq API provider — fastest free inference."""

    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.enabled = bool(self.api_key)
        self.base_url = GROQ_BASE_URL
        self._http = None

    def is_available(self) -> bool:
        return self.enabled and bool(self.api_key)

    def _get_http(self):
        if self._http is None:
            import httpx
            self._http = httpx.AsyncClient(timeout=60)
        return self._http

    async def complete(
        self,
        messages: list[dict],
        model_tier: str = "balanced",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        if not self.is_available():
            raise RuntimeError("Groq not configured — add GROQ_API_KEY to .env")

        model = GROQ_MODELS.get(model_tier, GROQ_MODELS["balanced"])
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        http = self._get_http()
        resp = await http.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def complete_fast(self, prompt: str) -> str:
        """Quick single-turn fast response using 8B model."""
        return await self.complete(
            [{"role": "user", "content": prompt}],
            model_tier="fast",
            max_tokens=1024,
        )

    def list_models(self) -> dict:
        return GROQ_MODELS

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()


# Global singleton
groq = GroqProvider()
