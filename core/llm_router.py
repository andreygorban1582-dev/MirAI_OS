"""
MirAI OS — Multi-Provider LLM Router
Intelligently routes requests across all available providers:
  1. OpenRouter (primary — Qwen 3.5 9B JOSIEFIED, 4 keys)
  2. Groq        (optional — fastest free inference)
  3. Together.ai (optional — large models, 72B Qwen)
  4. NotDiamond  (optional — automatic best-model routing)

Priority: NotDiamond route > Groq (if fast needed) > OpenRouter (primary) > Together (fallback)
All providers are optional — system works with just OpenRouter.
"""
from __future__ import annotations

import logging
import os
from typing import Optional, AsyncIterator

from core.config import cfg
from core.llm import llm as openrouter_llm

logger = logging.getLogger("mirai.llm_router")


class MultiProviderRouter:
    """
    Routes LLM requests to the best available provider.
    Falls back gracefully if any provider is unavailable.
    """

    def __init__(self) -> None:
        self._groq = None
        self._together = None
        self._notdiamond = None

    def _get_groq(self):
        if self._groq is None:
            try:
                from integrations.groq_provider import groq
                self._groq = groq
            except Exception:
                self._groq = False
        return self._groq if self._groq else None

    def _get_together(self):
        if self._together is None:
            try:
                from integrations.together_provider import together
                self._together = together
            except Exception:
                self._together = False
        return self._together if self._together else None

    def _get_notdiamond(self):
        if self._notdiamond is None:
            try:
                from integrations.notdiamond_router import router
                self._notdiamond = router
            except Exception:
                self._notdiamond = False
        return self._notdiamond if self._notdiamond else None

    def available_providers(self) -> list[str]:
        providers = ["openrouter"]
        groq = self._get_groq()
        if groq and groq.is_available():
            providers.append("groq")
        together = self._get_together()
        if together and together.is_available():
            providers.append("together")
        nd = self._get_notdiamond()
        if nd and nd.is_available():
            providers.append("notdiamond")
        return providers

    async def complete(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        task_hint: Optional[str] = None,
        prefer_fast: bool = False,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """
        Route and complete. task_hint guides provider selection:
        "code" | "web" | "short" | "long" | "creative" | "general"
        """
        # 1. Try NotDiamond routing first
        nd = self._get_notdiamond()
        if nd and nd.is_available():
            try:
                provider, model = await nd.route(messages, task_hint)
                result = await self._dispatch(
                    provider, model, messages, temperature, max_tokens, stream
                )
                if result:
                    logger.debug(f"NotDiamond routed → {provider}:{model}")
                    return result
            except Exception as e:
                logger.debug(f"NotDiamond routing failed: {e}")

        # 2. Prefer Groq for fast/short tasks
        groq = self._get_groq()
        if prefer_fast and groq and groq.is_available():
            try:
                result = await groq.complete(
                    messages,
                    model_tier="fast",
                    temperature=temperature or 0.7,
                    max_tokens=max_tokens or 2048,
                )
                logger.debug("Routed → Groq (fast)")
                return result
            except Exception as e:
                logger.debug(f"Groq fast failed: {e}")

        # 3. Primary: OpenRouter (Qwen 3.5 9B JOSIEFIED)
        try:
            result = await openrouter_llm.complete(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
            )
            logger.debug("Routed → OpenRouter (primary)")
            return result
        except Exception as e:
            logger.warning(f"OpenRouter failed: {e}")

        # 4. Fallback: Together.ai
        together = self._get_together()
        if together and together.is_available():
            try:
                model_key = "qwen-72b" if (max_tokens or 0) > 4000 else "qwen-7b"
                result = await together.complete(
                    messages,
                    model_key=model_key,
                    temperature=temperature or 0.7,
                    max_tokens=max_tokens or 4096,
                )
                logger.debug(f"Routed → Together.ai ({model_key})")
                return result
            except Exception as e:
                logger.warning(f"Together.ai fallback failed: {e}")

        # 5. Last resort: Groq balanced
        if groq and groq.is_available():
            try:
                result = await groq.complete(
                    messages,
                    model_tier="balanced",
                    temperature=temperature or 0.7,
                    max_tokens=max_tokens or 4096,
                )
                logger.debug("Routed → Groq (last resort)")
                return result
            except Exception as e:
                logger.error(f"All providers failed. Last error: {e}")

        raise RuntimeError("All LLM providers exhausted. Check API keys.")

    async def _dispatch(
        self,
        provider: str,
        model: str,
        messages: list[dict],
        temperature: Optional[float],
        max_tokens: Optional[int],
        stream: bool,
    ):
        if provider == "openrouter":
            return await openrouter_llm.complete(
                messages, model=model,
                temperature=temperature, max_tokens=max_tokens, stream=stream,
            )
        elif provider == "groq":
            groq = self._get_groq()
            if groq and groq.is_available():
                return await groq.complete(
                    messages, model_tier="balanced",
                    temperature=temperature or 0.7,
                    max_tokens=max_tokens or 4096,
                )
        elif provider == "together":
            together = self._get_together()
            if together and together.is_available():
                return await together.complete(
                    messages, model_key="qwen-7b",
                    temperature=temperature or 0.7,
                    max_tokens=max_tokens or 4096,
                )
        return None

    def status(self) -> dict:
        return {
            "providers": self.available_providers(),
            "openrouter_keys": len(cfg.openrouter_keys),
            "groq": self._get_groq() is not None and bool(getattr(self._get_groq(), "enabled", False)),
            "together": self._get_together() is not None and bool(getattr(self._get_together(), "enabled", False)),
            "notdiamond": self._get_notdiamond() is not None and bool(getattr(self._get_notdiamond(), "enabled", False)),
        }


# Global singleton
llm_router = MultiProviderRouter()
