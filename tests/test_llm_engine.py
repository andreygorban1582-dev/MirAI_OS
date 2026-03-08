"""
Tests for LLM Engine (mocked OpenRouter calls).
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_build_messages_includes_system():
    from core.llm_engine import LLMEngine
    engine = LLMEngine()
    messages = engine._build_messages("hello", None)
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "hello"


@pytest.mark.asyncio
async def test_trim_history_respects_context():
    from core.llm_engine import LLMEngine
    engine = LLMEngine()
    engine.max_context = 100  # Very small context to force trimming

    # Each message is 60 chars (> context budget of 100*3=300 total)
    history = [
        {"role": "user", "content": "a" * 60},
        {"role": "assistant", "content": "b" * 60},
        {"role": "user", "content": "c" * 60},
        {"role": "assistant", "content": "d" * 60},
        {"role": "user", "content": "e" * 60},
        {"role": "assistant", "content": "f" * 60},
    ]
    trimmed = engine._trim_history(history)
    # Total chars should fit within max_context * 3 = 300
    total_chars = sum(len(m["content"]) for m in trimmed)
    assert total_chars <= engine.max_context * 3


@pytest.mark.asyncio
async def test_chat_returns_string(monkeypatch):
    from core.llm_engine import LLMEngine

    async def fake_completion(self, messages, temperature):
        return "Fuhahaha! Test response."

    monkeypatch.setattr(LLMEngine, "_completion", fake_completion)
    engine = LLMEngine()
    engine._client = MagicMock()  # Bypass context manager check
    engine._request_semaphore = asyncio.Semaphore(1)
    result = await engine.chat("test message")
    assert result == "Fuhahaha! Test response."


def test_llm_engine_default_model():
    from core.llm_engine import LLMEngine
    from config.settings import settings
    engine = LLMEngine()
    assert engine.model == settings.default_model
