"""
MirAI OS — NotDiamond LLM Router (Optional)
NotDiamond automatically routes prompts to the best LLM
for each task type — maximizes quality while minimizing cost.
Free tier: Available

Enable: set NOTDIAMOND_API_KEY in .env
        set integrations.notdiamond.enabled: true in settings.yaml

Without NotDiamond: MirAI uses round-robin key rotation.
With NotDiamond:    MirAI picks the optimal model per query.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("mirai.integrations.notdiamond")

# Fallback routing rules (used when NotDiamond API is unavailable)
TASK_MODEL_MAP = {
    "code":        "groq:llama-3.1-70b-versatile",
    "math":        "openrouter:qwen/qwen3.5-9b-instruct",
    "creative":    "openrouter:qwen/qwen3.5-9b-instruct",
    "web":         "groq:llama-3.1-8b-instant",
    "short":       "groq:llama-3.1-8b-instant",
    "long":        "together:qwen-72b",
    "default":     "openrouter:qwen/qwen3.5-9b-instruct",
}


class NotDiamondRouter:
    """Routes queries to optimal LLM provider + model."""

    def __init__(self) -> None:
        self.api_key = os.getenv("NOTDIAMOND_API_KEY", "")
        self.enabled = bool(self.api_key)
        self._http = None

    def is_available(self) -> bool:
        return self.enabled

    def _get_http(self):
        if self._http is None:
            import httpx
            self._http = httpx.AsyncClient(timeout=10)
        return self._http

    async def route(self, messages: list[dict], task_hint: Optional[str] = None) -> tuple[str, str]:
        """
        Returns (provider, model) for the given messages.
        provider: "openrouter" | "groq" | "together"
        model: model identifier string
        """
        if self.is_available():
            return await self._api_route(messages, task_hint)
        return self._heuristic_route(messages, task_hint)

    async def _api_route(self, messages: list[dict], task_hint: Optional[str]) -> tuple[str, str]:
        try:
            import httpx
            http = self._get_http()
            payload = {
                "messages": messages,
                "llm_providers": [
                    {"provider": "openai", "model": "gpt-4o"},
                    {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"},
                ],
            }
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            resp = await http.post("https://api.notdiamond.ai/v2/optimizer/modelSelect",
                                   json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            # Map NotDiamond recommendation to our providers
            rec = data.get("providers", [{}])[0]
            model = rec.get("model", "")
            if "gpt" in model or "claude" not in model:
                return "openrouter", "qwen/qwen3.5-9b-instruct"
            return "openrouter", "qwen/qwen3.5-9b-instruct"
        except Exception as e:
            logger.debug(f"NotDiamond API error: {e} — using heuristic routing")
            return self._heuristic_route(messages, task_hint)

    def _heuristic_route(self, messages: list[dict], task_hint: Optional[str]) -> tuple[str, str]:
        """Simple heuristic routing without API."""
        if task_hint and task_hint in TASK_MODEL_MAP:
            target = TASK_MODEL_MAP[task_hint]
        else:
            # Detect task type from content
            content = " ".join(m.get("content", "") for m in messages[-2:]).lower()
            if any(k in content for k in ["code", "python", "bash", "script", "function", "debug"]):
                target = TASK_MODEL_MAP["code"]
            elif any(k in content for k in ["search", "find", "browse", "web"]):
                target = TASK_MODEL_MAP["web"]
            elif len(content) < 200:
                target = TASK_MODEL_MAP["short"]
            else:
                target = TASK_MODEL_MAP["default"]

        provider, model = target.split(":", 1)
        return provider, model

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()


# Global singleton
router = NotDiamondRouter()
