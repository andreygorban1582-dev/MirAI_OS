"""
MirAI OS — LLM Layer
Handles 4-key OpenRouter rotation, streaming, retries, and fallbacks.
Supports Qwen 3.5 9B (JOSIEFIED/Abliterated) as primary model.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import AsyncIterator, Optional

import httpx

from core.config import cfg

logger = logging.getLogger("mirai.llm")


class KeyUsageTracker:
    """Track usage and health per API key for smart rotation."""

    def __init__(self, keys: list[str]) -> None:
        self.keys = keys
        self.usage: dict[str, int] = defaultdict(int)
        self.errors: dict[str, int] = defaultdict(int)
        self.last_used: dict[str, float] = defaultdict(float)
        self._rr_index = 0

    def get_key(self, strategy: str = "round_robin") -> str:
        if not self.keys:
            raise RuntimeError("No OpenRouter API keys configured!")

        if strategy == "least_used":
            return min(self.keys, key=lambda k: self.usage[k])
        elif strategy == "random":
            import random
            return random.choice(self.keys)
        else:  # round_robin
            key = self.keys[self._rr_index % len(self.keys)]
            self._rr_index += 1
            return key

    def record_success(self, key: str) -> None:
        self.usage[key] += 1
        self.last_used[key] = time.time()

    def record_error(self, key: str) -> None:
        self.errors[key] += 1

    def status(self) -> list[dict]:
        return [
            {
                "key_suffix": k[-8:],
                "requests": self.usage[k],
                "errors": self.errors[k],
                "last_used": self.last_used[k],
            }
            for k in self.keys
        ]


class LLMClient:
    """Async OpenRouter client with key rotation and streaming."""

    def __init__(self) -> None:
        self.base_url = cfg.llm.get("base_url", "https://openrouter.ai/api/v1")
        self.primary_model = cfg.llm.get("primary_model", "qwen/qwen3.5-9b-instruct")
        self.fallback_model = cfg.llm.get("fallback_model", "qwen/qwen2.5-7b-instruct")
        self.strategy = cfg.llm.get("key_rotation_strategy", "round_robin")
        self.max_retries = int(cfg.llm.get("max_retries", 4))
        self.timeout = float(cfg.llm.get("request_timeout", 120))
        self.max_tokens = int(cfg.llm.get("max_tokens", 8192))
        self.temperature = float(cfg.llm.get("temperature", 0.85))
        self.tracker = KeyUsageTracker(cfg.openrouter_keys)
        self._http = httpx.AsyncClient(timeout=self.timeout)

    async def _headers(self, key: str) -> dict:
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/MirAI-OS",
            "X-Title": "MirAI OS",
        }

    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """Send a completion request. Returns full string or async generator for stream."""
        target_model = model or self.primary_model
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens or self.max_tokens

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens,
            "stream": stream,
        }

        last_exc: Exception | None = None
        tried_models = [target_model]

        for attempt in range(self.max_retries + 1):
            key = self.tracker.get_key(self.strategy)
            try:
                if stream:
                    return self._stream_response(key, payload, attempt)
                resp = await self._http.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=await self._headers(key),
                )
                resp.raise_for_status()
                data = resp.json()
                self.tracker.record_success(key)
                return data["choices"][0]["message"]["content"]

            except httpx.HTTPStatusError as e:
                self.tracker.record_error(key)
                last_exc = e

                # 429 → rate limited, rotate immediately
                if e.response.status_code == 429:
                    logger.warning(f"Key ...{key[-8:]} rate limited. Rotating.")
                    continue

                # 404 model not found → try fallback model
                if e.response.status_code == 404 and self.fallback_model not in tried_models:
                    logger.warning(f"Model {target_model} not found, falling back.")
                    payload["model"] = self.fallback_model
                    tried_models.append(self.fallback_model)
                    continue

                logger.error(f"LLM HTTP error {e.response.status_code}: {e}")

            except Exception as e:
                self.tracker.record_error(key)
                last_exc = e
                logger.error(f"LLM request error (attempt {attempt+1}): {e}")

            # Exponential backoff
            if attempt < self.max_retries:
                wait = 2 ** attempt
                logger.info(f"Retrying in {wait}s...")
                await asyncio.sleep(wait)

        raise RuntimeError(f"LLM request failed after {self.max_retries} retries: {last_exc}")

    async def _stream_response(
        self, key: str, payload: dict, attempt: int
    ) -> AsyncIterator[str]:
        """Yield token chunks as they arrive."""
        async with self._http.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=await self._headers(key),
        ) as resp:
            resp.raise_for_status()
            self.tracker.record_success(key)
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        import json
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        continue

    async def close(self) -> None:
        await self._http.aclose()

    def key_status(self) -> list[dict]:
        return self.tracker.status()


# Global singleton
llm = LLMClient()
