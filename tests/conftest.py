"""Shared pytest fixtures.

The whole suite runs with NO Ollama and NO network.  Offline fakes live in
``tests/fakes.py``:

* :class:`FakeVectorStore` mimics the ChromaDB contract in pure Python (cosine
  ranking over stored vectors), so memory tools and the agent graph exercise
  real recall logic without the heavy Chroma dependency.
* :class:`FakeLLM` returns deterministic, schema-correct responses per prompt.

:class:`HashingEmbeddings` (the real offline embedder) provides genuinely
lexical vectors.
"""

from __future__ import annotations

import pytest

from src.memory.embeddings import HashingEmbeddings
from src.memory.sqlite_store import SQLiteStore
from tests.fakes import FakeLLM, FakeVectorStore


@pytest.fixture
def hashing() -> HashingEmbeddings:
    return HashingEmbeddings()


@pytest.fixture
def fake_vector() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture
def sqlite_store(tmp_path) -> SQLiteStore:
    store = SQLiteStore(tmp_path / "research.db")
    store.initialize()
    return store


@pytest.fixture
def settings(tmp_path):
    from src.config import Settings

    return Settings(
        db_path=tmp_path / "research.db",
        chroma_dir=tmp_path / "chroma",
        log_file=tmp_path / "agent.log",
        memory_relevance_threshold=0.0,
        recall_shortcircuit_hits=2,
    )


@pytest.fixture
def offline_agent(settings, sqlite_store, fake_vector, monkeypatch):
    """A fully wired :class:`ResearchAgent` with canned web tools and a fake LLM.

    Returns ``(agent, tools, sqlite_store, fake_vector, calls)`` where ``calls``
    counts web-tool invocations.
    """
    from src.agent.graph import ResearchAgent
    from src.agent.state import AgentDeps
    from src.agent.tool_client import ToolClient

    tools = ToolClient(HashingEmbeddings(), sqlite_store, fake_vector, settings)
    calls = {"search": 0, "scrape": 0}

    def fake_search(query, max_results=None):
        calls["search"] += 1
        return [
            {
                "title": "Redis Guide",
                "url": "https://example.com/redis",
                "snippet": "Redis is an in-memory key-value data store used for caching.",
            },
            {
                "title": "Memcached Guide",
                "url": "https://example.com/memcached",
                "snippet": "Memcached is a distributed memory caching system.",
            },
        ]

    def fake_scrape(url):
        calls["scrape"] += 1
        return {
            "url": url,
            "title": "Guide",
            "text": ("An in-memory data store used for caching and sessions. " * 12),
            "word_count": 96,
            "method_used": "static",
        }

    monkeypatch.setattr(tools, "web_search", fake_search)
    monkeypatch.setattr(tools, "scrape_page", fake_scrape)

    deps = AgentDeps(llm=FakeLLM(), tools=tools, sqlite=sqlite_store, settings=settings)
    return ResearchAgent(deps), tools, sqlite_store, fake_vector, calls
