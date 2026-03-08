"""
LLM Engine — OpenRouter Integration with Legion Go Optimizations
Handles all AI inference requests with hardware-aware context management.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncGenerator, Optional

import httpx

from config.settings import settings


class LLMEngine:
    """
    Async LLM engine backed by OpenRouter API.

    Tuned for Legion Go (AMD Ryzen Z1 Extreme, 16 GB RAM, 780M iGPU):
    - Dynamic context window sizing based on available RAM
    - Adaptive retry with exponential back-off
    - Streaming inference for low-latency responses
    - Prompt compression to keep tokens under budget
    """

    DEFAULT_SYSTEM = (
        "You are MirAI, an advanced AI assistant running on MirAI_OS. "
        "You are knowledgeable, helpful, and efficient."
    )

    def __init__(
        self,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> None:
        self.model = model or settings.default_model
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM
        self.max_tokens = max_tokens
        self._client: httpx.AsyncClient | None = None

        # Legion Go hardware-aware limits
        ai_cfg = settings.legion_go_ai_settings()
        self.max_context = ai_cfg.get("max_context_tokens", settings.max_context_tokens)
        self._request_semaphore = asyncio.Semaphore(
            ai_cfg.get("max_batch_size", 4)
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "LLMEngine":
        self._client = httpx.AsyncClient(
            base_url=settings.openrouter_base_url,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "https://github.com/andreygorban1582-dev/MirAI_OS",
                "X-Title": "MirAI_OS",
            },
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chat(
        self,
        user_message: str,
        history: list[dict] | None = None,
        stream: bool = False,
        temperature: float = 0.7,
    ) -> str:
        """Send a chat message and return the assistant reply."""
        messages = self._build_messages(user_message, history)
        async with self._request_semaphore:
            if stream:
                chunks: list[str] = []
                async for chunk in self._stream_completion(messages, temperature):
                    chunks.append(chunk)
                return "".join(chunks)
            return await self._completion(messages, temperature)

    async def stream_chat(
        self,
        user_message: str,
        history: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Yield streaming tokens for real-time display."""
        messages = self._build_messages(user_message, history)
        async with self._request_semaphore:
            async for chunk in self._stream_completion(messages, temperature):
                yield chunk

    async def embed(self, text: str) -> list[float]:
        """Get an embedding vector for the provided text (OpenRouter passthrough)."""
        assert self._client is not None, "Use 'async with LLMEngine()' context manager"
        response = await self._client.post(
            "/embeddings",
            json={"model": "openai/text-embedding-ada-002", "input": text},
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        user_message: str,
        history: list[dict] | None,
    ) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": self.system_prompt}]
        if history:
            # Keep only recent turns that fit context budget
            messages.extend(self._trim_history(history))
        messages.append({"role": "user", "content": user_message})
        return messages

    def _trim_history(self, history: list[dict]) -> list[dict]:
        """Drop oldest turns to stay within max_context budget (rough token count)."""
        max_hist_chars = self.max_context * 3  # ~3 chars per token estimate
        result: list[dict] = []
        total = 0
        for turn in reversed(history):
            turn_len = len(turn.get("content", ""))
            if total + turn_len > max_hist_chars:
                break
            result.insert(0, turn)
            total += turn_len
        return result

    async def _completion(
        self, messages: list[dict], temperature: float
    ) -> str:
        assert self._client is not None
        for attempt in range(3):
            try:
                resp = await self._client.post(
                    "/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": self.max_tokens,
                        "temperature": temperature,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
        return ""

    async def _stream_completion(
        self, messages: list[dict], temperature: float
    ) -> AsyncGenerator[str, None]:
        assert self._client is not None
        async with self._client.stream(
            "POST",
            "/chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": temperature,
                "stream": True,
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    return
                import json
                try:
                    payload = json.loads(data)
                    delta = payload["choices"][0].get("delta", {})
                    if content := delta.get("content"):
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
