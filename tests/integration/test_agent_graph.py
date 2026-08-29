"""Integration tests for the LangGraph agent, end-to-end and fully offline.

Exercises the real Plan -> Research -> Synthesize -> Format pipeline with canned
web tools and a deterministic fake LLM (see ``conftest.offline_agent``).
"""

from __future__ import annotations

from src.agent.graph import ResearchAgent
from src.agent.state import AgentDeps
from src.agent.tool_client import ToolClient
from src.memory.embeddings import HashingEmbeddings
from src.memory.sqlite_store import SQLiteStore
from tests.fakes import FakeLLM, FakeVectorStore


def test_brief_run_produces_cited_output(offline_agent):
    agent, tools, sqlite_store, vector, calls = offline_agent
    state = agent.run("Compare Redis and Memcached", "brief", "apa")

    out = state["final_output"]
    assert "# Research Brief" in out
    assert "## References" in out
    assert calls["search"] == 2          # one per sub-question
    assert calls["scrape"] > 0
    # Findings + citations persisted to SQLite.
    session = sqlite_store.get_session(state["session_id"])
    assert session["status"] == "completed"
    assert len(session["findings"]) == 2
    assert session["findings"][0]["citations"]
    # Each finding was written back into semantic memory (AG-06).
    assert vector.count() == 2
    # The live trace was populated for the UI.
    assert len(state["trace"]) >= 4


def test_report_format(offline_agent):
    agent, *_ = offline_agent
    state = agent.run("Explain event sourcing", "report", "apa")
    assert "## Executive summary" in state["final_output"]
    assert "*Insight Report" in state["final_output"]


def test_comparison_format_builds_table(offline_agent):
    agent, *_ = offline_agent
    state = agent.run("Redis vs Memcached", "comparison", "apa")
    out = state["final_output"]
    assert "| Dimension | Redis | Memcached |" in out
    assert "Overview" in out


def test_stream_yields_progressive_state(offline_agent):
    agent, *_ = offline_agent
    snapshots = list(agent.stream("What is Redis?", "brief", "apa"))
    assert len(snapshots) >= 2
    # Trace grows monotonically as nodes run.
    lengths = [len(s.get("trace", [])) for s in snapshots]
    assert lengths == sorted(lengths)
    assert snapshots[-1].get("final_output")


def _build_agent(settings, llm):
    """Helper: build an offline agent with an injectable sub-question set."""
    vector = FakeVectorStore()
    sqlite = SQLiteStore(settings.db_path)
    sqlite.initialize()
    tools = ToolClient(HashingEmbeddings(), sqlite, vector, settings)
    deps = AgentDeps(llm=llm, tools=tools, sqlite=sqlite, settings=settings)
    return ResearchAgent(deps), tools, vector, sqlite


def test_recall_before_search_short_circuits(settings, monkeypatch):
    """If memory already answers a sub-question, the web is never queried (AG-03)."""
    llm = FakeLLM(sub_questions=["What is Redis?"])
    agent, tools, vector, sqlite = _build_agent(settings, llm)

    # Pre-load two strongly-matching memories so recall returns >= 2 hits.
    emb = HashingEmbeddings()
    for i in range(2):
        vector.add(
            f"seed:{i}",
            "Redis is an in-memory key value store used for caching sessions.",
            emb.embed(["Redis is an in-memory key value store used for caching sessions."])[0],
            {"session_id": f"old{i}"},
        )

    searched = {"n": 0}
    monkeypatch.setattr(tools, "web_search", lambda *a, **k: searched.__setitem__("n", searched["n"] + 1) or [])

    state = agent.run("What is Redis?", "brief", "apa")
    assert searched["n"] == 0          # short-circuited on memory
    assert any("memory" in e["title"].lower() for e in state["trace"])


def test_partial_source_failure_degrades_to_snippet(settings, monkeypatch):
    """A failed scrape falls back to the search snippet and records a warning (AG-07)."""
    llm = FakeLLM(sub_questions=["What is Redis?"])
    agent, tools, vector, sqlite = _build_agent(settings, llm)

    monkeypatch.setattr(
        tools,
        "web_search",
        lambda *a, **k: [
            {"title": "Good", "url": "https://ok.example", "snippet": "Redis snippet text."},
            {"title": "Bad", "url": "https://bad.example", "snippet": "fallback snippet."},
        ],
    )

    def flaky_scrape(url):
        if "bad" in url:
            return {"url": url, "title": "", "text": "", "word_count": 0,
                    "method_used": "failed", "error": "boom"}
        return {"url": url, "title": "Good", "text": "Redis is in-memory. " * 20,
                "word_count": 60, "method_used": "static"}

    monkeypatch.setattr(tools, "scrape_page", flaky_scrape)

    state = agent.run("What is Redis?", "brief", "apa")
    assert state["warnings"]                       # degradation recorded
    assert "final_output" in state
    session = sqlite.get_session(state["session_id"])
    # Finding still produced despite one bad source.
    assert len(session["findings"]) == 1


def test_cross_session_memory_reuse(settings, monkeypatch):
    """A finding stored in one session is recalled in a later session (AC-09)."""
    llm = FakeLLM(sub_questions=["What is Redis?"])
    agent, tools, vector, sqlite = _build_agent(settings, llm)
    monkeypatch.setattr(
        tools, "web_search",
        lambda *a, **k: [{"title": "R", "url": "https://ok.example", "snippet": "Redis is in-memory."}],
    )
    monkeypatch.setattr(
        tools, "scrape_page",
        lambda url: {"url": url, "title": "R", "text": "Redis is an in-memory store. " * 20,
                     "word_count": 60, "method_used": "static"},
    )

    first = agent.run("What is Redis?", "brief", "apa")
    assert vector.count() >= 1

    # Second run: recall should now surface the first run's finding.
    hits = tools.recall_memory("all", "What is Redis?", top_k=5, threshold=0.0)
    assert any(h["session_id"] == first["session_id"] for h in hits)
