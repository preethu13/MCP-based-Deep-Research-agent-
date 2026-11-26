"""Unit tests for the SQLite structured store, including cascade deletes."""

from __future__ import annotations

import sqlite3

import pytest

from src.memory.sqlite_store import SQLiteStore


def test_initialize_is_idempotent(tmp_path):
    store = SQLiteStore(tmp_path / "r.db")
    store.initialize()
    store.initialize()  # must not raise
    assert store.list_sessions() == []


def test_session_findings_and_citations_roundtrip(sqlite_store: SQLiteStore):
    sqlite_store.create_session("s1", "Redis vs Memcached", "brief")
    fid = sqlite_store.add_finding("s1", "What is Redis?", "Redis is in-memory.", 0.9)
    sqlite_store.add_citation(fid, "https://redis.io", "Redis", None, None, "APA", "MLA")

    session = sqlite_store.get_session("s1")
    assert session is not None
    assert session["user_query"] == "Redis vs Memcached"
    assert len(session["findings"]) == 1
    finding = session["findings"][0]
    assert finding["claim_text"] == "Redis is in-memory."
    assert finding["citations"][0]["formatted_apa"] == "APA"


def test_list_sessions_counts_findings(sqlite_store: SQLiteStore):
    sqlite_store.create_session("s1", "q", "brief")
    sqlite_store.add_finding("s1", "a", "claim a")
    sqlite_store.add_finding("s1", "b", "claim b")
    rows = sqlite_store.list_sessions()
    assert rows[0]["session_id"] == "s1"
    assert rows[0]["finding_count"] == 2


def test_delete_session_cascades(sqlite_store: SQLiteStore):
    sqlite_store.create_session("s1", "q", "brief")
    fid = sqlite_store.add_finding("s1", "a", "claim")
    sqlite_store.add_citation(fid, "https://x", "X")
    sqlite_store.add_memory_pointer("s1", "vec-1", "summary")

    assert sqlite_store.delete_session("s1") is True
    assert sqlite_store.get_session("s1") is None
    assert sqlite_store.get_memory_pointer("vec-1") is None
    # Citation is gone too (cascade through findings).
    with sqlite_store._connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM citations").fetchone()[0] == 0


def test_delete_missing_session_returns_false(sqlite_store: SQLiteStore):
    assert sqlite_store.delete_session("nope") is False


def test_search_sessions_like(sqlite_store: SQLiteStore):
    sqlite_store.create_session("s1", "Redis caching", "brief")
    sqlite_store.create_session("s2", "GraphQL basics", "report")
    hits = sqlite_store.search_sessions("redis")
    assert [h["session_id"] for h in hits] == ["s1"]


def test_foreign_key_enforced_for_orphan_finding(sqlite_store: SQLiteStore):
    with pytest.raises(sqlite3.IntegrityError):
        sqlite_store.add_finding("ghost-session", "q", "claim")


def test_memory_pointer_roundtrip(sqlite_store: SQLiteStore):
    sqlite_store.create_session("s1", "q", "brief")
    sqlite_store.add_memory_pointer("s1", "vec-42", "a summary")
    ptr = sqlite_store.get_memory_pointer("vec-42")
    assert ptr is not None
    assert ptr["summary_text"] == "a summary"
    assert ptr["session_id"] == "s1"


def test_save_and_find_completed_session(sqlite_store: SQLiteStore):
    sqlite_store.create_session("s10", "Context Rot in LLMs", "report")
    mock_findings = [{"sub_question": "What is context rot?", "claim": "Context rot is degradation."}]
    sqlite_store.save_session_result("s10", "# Context Rot Report\nFull content.", mock_findings)

    found = sqlite_store.find_completed_session("Context Rot", output_format="report")
    assert found is not None
    assert found["session_id"] == "s10"
    assert "Context Rot Report" in found["final_output"]
    assert len(found["findings"]) == 1
    assert found["findings"][0]["claim"] == "Context Rot is degradation." or "context rot" in found["findings"][0]["claim"].lower()

    # Different format shouldn't match
    assert sqlite_store.find_completed_session("Context Rot", output_format="brief") is None
