"""Unit tests for lenient JSON parsing and the offline DemoLLM."""

from __future__ import annotations

import pytest

from src.agent.demo import DemoLLM
from src.agent.llm import loads_lenient


def test_loads_lenient_plain_json():
    assert loads_lenient('["a", "b"]') == ["a", "b"]


def test_loads_lenient_strips_code_fence():
    assert loads_lenient('```json\n{"x": 1}\n```') == {"x": 1}


def test_loads_lenient_finds_embedded_block():
    assert loads_lenient('Sure! Here it is: ["one", "two"] hope that helps') == ["one", "two"]


def test_loads_lenient_raises_without_json():
    with pytest.raises(ValueError):
        loads_lenient("no json here at all")


def test_demo_planner_returns_subquestions():
    llm = DemoLLM()
    data = llm.complete_json(
        "You are a meticulous research planner.",
        "User question: Compare Redis and Memcached\nDesired output format: brief.",
    )
    assert isinstance(data, list)
    assert len(data) >= 2


def test_demo_comparison_returns_entities():
    llm = DemoLLM()
    data = llm.complete_json(
        "You convert research notes into a structured comparison.",
        "Question: Redis vs Memcached\n\nResearch notes:\n...",
    )
    assert "entities" in data
    assert len(data["entities"]) >= 2


def test_demo_synthesis_condenses_context_without_inventing():
    llm = DemoLLM()
    out = llm.complete(
        "You are a careful research analyst.",
        "Sub-question: What is Redis?\n\nSources:\nRedis is fast. It stores data in memory.",
    )
    assert "Redis is fast" in out
    assert "Demo mode" in out


def test_demo_ping_ok():
    assert DemoLLM().ping()[0] is True
