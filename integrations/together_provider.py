"""
MirAI OS — Together.ai Integration (Optional)
Together.ai has free inference for open-source models.
Great for: Llama 3, Qwen, Mistral, DeepSeek, Gemma
Free: $1 credit on signup + some permanently free models

Enable: set TOGETHER_API_KEY in .env
        set integrations.together.enabled: true in settings.yaml
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("mirai.integrations.together")

TOGETHER_BASE_URL = "https://api.together.xyz/v1"
TOGETHER_FREE_MODELS = {
    "qwen-72b":     "Qwen/Qwen2.5-72B-Instruct-Turbo",
    "llama-70b":    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "deepseek-67b": "deepseek-ai/deepseek-llm-67b-chat",
    "mixtral":      "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "gemma-27b":    "google/gemma-2-27b-it",
    "qwen-7b":      "Qwen/Qwen2.5-7B-Instruct-Turbo",     # Fastest
}


class TogetherProvider:
    """Together.ai inference provider."""

    def __init__(self) -> None:
        self.api_key = os.getenv("TOGETHER_API_KEY", "")
        self.enabled = bool(self.api_key)
        self._http = None

    def is_available(self) -> bool:
        return self.enabled

    def _get_http(self):
        if self._http is None:
            import httpx
            self._http = httpx.AsyncClient(timeout=120)
        return self._http

    async def complete(
        self,
        messages: list[dict],
        model_key: str = "qwen-7b",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        if not self.is_available():
            raise RuntimeError("Together.ai not configured — add TOGETHER_API_KEY to .env")

        model = TOGETHER_FREE_MODELS.get(model_key, TOGETHER_FREE_MODELS["qwen-7b"])
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
        resp = await http.post(f"{TOGETHER_BASE_URL}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def list_models(self) -> dict:
        return TOGETHER_FREE_MODELS

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()


# Global singleton
together = TogetherProvider()
