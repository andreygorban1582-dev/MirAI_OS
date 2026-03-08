"""
Tests for the Agent Flow.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import json


@pytest.mark.asyncio
async def test_parse_action_valid():
    from core.agent_flow import AgentFlow
    agent = AgentFlow()
    text = '{"tool": "think", "thought": "I need to reason about this"}'
    action = agent._parse_action(text)
    assert action is not None
    assert action["tool"] == "think"


@pytest.mark.asyncio
async def test_parse_action_embedded():
    from core.agent_flow import AgentFlow
    agent = AgentFlow()
    text = 'Here is my response: {"tool": "finish", "answer": "42"} end.'
    action = agent._parse_action(text)
    assert action is not None
    assert action["tool"] == "finish"
    assert action["answer"] == "42"


@pytest.mark.asyncio
async def test_parse_action_invalid():
    from core.agent_flow import AgentFlow
    agent = AgentFlow()
    result = agent._parse_action("This has no JSON at all.")
    assert result is None


@pytest.mark.asyncio
async def test_python_tool():
    from core.agent_flow import _tool_python
    result = await _tool_python("result = 2 + 2\nprint('calculated')")
    assert "4" in result or "calculated" in result


@pytest.mark.asyncio
async def test_python_tool_error():
    from core.agent_flow import _tool_python
    result = await _tool_python("raise ValueError('test error')")
    assert "Error" in result


@pytest.mark.asyncio
async def test_read_file_missing():
    from core.agent_flow import _tool_read_file
    result = await _tool_read_file("/nonexistent/path/file.txt")
    assert "Error" in result


@pytest.mark.asyncio
async def test_agent_returns_final_answer(tmp_path, monkeypatch):
    """Agent should return the finish tool's answer when LLM provides it."""
    from core.agent_flow import AgentFlow
    from core.llm_engine import LLMEngine

    async def fake_chat(self, message, history=None, stream=False, temperature=0.7):
        return json.dumps({"tool": "finish", "answer": "the answer is 42"})

    monkeypatch.setattr(LLMEngine, "chat", fake_chat)

    async def fake_enter(self):
        self._client = object()
        return self

    async def fake_exit(self, *args):
        pass

    monkeypatch.setattr(LLMEngine, "__aenter__", fake_enter)
    monkeypatch.setattr(LLMEngine, "__aexit__", fake_exit)

    agent = AgentFlow()
    result = await agent.run("What is 6 * 7?")
    assert "42" in result
