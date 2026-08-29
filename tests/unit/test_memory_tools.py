"""Unit tests for ``store_memory`` / ``recall_memory`` over a fake vector store."""

from __future__ import annotations

from src.tools.memory import recall_memory, store_memory


def test_store_memory_returns_vector_id(fake_vector, hashing):
    result = store_memory(
        "s1", "Redis is an in-memory store.", {"topic": "redis"},
        vector_store=fake_vector, embeddings=hashing,
    )
    assert result["status"] == "stored"
    assert result["vector_id"].startswith("s1:")
    assert fake_vector.count() == 1


def test_store_memory_skips_empty_content(fake_vector, hashing):
    result = store_memory("s1", "   ", {}, vector_store=fake_vector, embeddings=hashing)
    assert result["status"] == "skipped"
    assert fake_vector.count() == 0


def test_store_memory_writes_sqlite_pointer(fake_vector, hashing, sqlite_store):
    sqlite_store.create_session("s1", "q", "brief")
    result = store_memory(
        "s1", "Some finding text.", {},
        vector_store=fake_vector, sqlite_store=sqlite_store, embeddings=hashing,
    )
    assert sqlite_store.get_memory_pointer(result["vector_id"]) is not None


def test_recall_finds_relevant_content(fake_vector, hashing):
    store_memory(
        "s1", "Redis is an in-memory key value store used for caching.", {},
        vector_store=fake_vector, embeddings=hashing,
    )
    hits = recall_memory(
        "all", "redis in-memory key value caching", top_k=5,
        vector_store=fake_vector, embeddings=hashing, threshold=0.0,
    )
    assert len(hits) == 1
    assert "Redis" in hits[0]["content"]
    assert hits[0]["similarity_score"] > 0.0


def test_recall_threshold_filters(fake_vector, hashing):
    store_memory("s1", "totally unrelated content about gardening", {},
                 vector_store=fake_vector, embeddings=hashing)
    hits = recall_memory(
        "all", "quantum chromodynamics lagrangian", top_k=5,
        vector_store=fake_vector, embeddings=hashing, threshold=0.99,
    )
    assert hits == []


def test_recall_scopes_by_session(fake_vector, hashing):
    store_memory("s1", "Redis caching notes", {}, vector_store=fake_vector, embeddings=hashing)
    store_memory("s2", "Redis caching notes", {}, vector_store=fake_vector, embeddings=hashing)

    scoped = recall_memory("s1", "redis caching", vector_store=fake_vector,
                           embeddings=hashing, threshold=0.0)
    assert {h["session_id"] for h in scoped} == {"s1"}

    everywhere = recall_memory("all", "redis caching", vector_store=fake_vector,
                               embeddings=hashing, threshold=0.0)
    assert {h["session_id"] for h in everywhere} == {"s1", "s2"}


def test_recall_empty_query_returns_empty(fake_vector, hashing):
    assert recall_memory("all", "  ", vector_store=fake_vector, embeddings=hashing) == []
