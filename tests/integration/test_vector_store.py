"""Integration test for the real ChromaDB-backed vector store.

Skipped automatically if ``chromadb`` is not importable.  Embeddings are computed
with the offline :class:`HashingEmbeddings`, so no Ollama is required.
"""

from __future__ import annotations

import pytest

pytest.importorskip("chromadb")

from src.memory.embeddings import HashingEmbeddings  # noqa: E402
from src.memory.vector_store import VectorStore  # noqa: E402


@pytest.fixture
def store(tmp_path):
    return VectorStore(tmp_path / "chroma", collection_name="test_memories")


def test_add_and_query_ranks_by_similarity(store):
    emb = HashingEmbeddings()
    docs = {
        "d1": "Redis is an in-memory key value data store used for caching.",
        "d2": "Memcached is a distributed memory caching system.",
        "d3": "Photosynthesis converts sunlight into chemical energy in plants.",
    }
    for vid, text in docs.items():
        store.add(vid, text, emb.embed([text])[0], {"session_id": "s1"})

    assert store.count() == 3
    query = emb.embed(["redis in-memory caching key value"])[0]
    hits = store.query(query, top_k=3)
    assert hits[0]["id"] == "d1"
    assert 0.0 <= hits[0]["similarity"] <= 1.0
    assert hits[0]["similarity"] >= hits[-1]["similarity"]


def test_metadata_filter_and_delete(store):
    emb = HashingEmbeddings()
    store.add("a", "alpha text about caches", emb.embed(["alpha text about caches"])[0], {"session_id": "s1"})
    store.add("b", "beta text about caches", emb.embed(["beta text about caches"])[0], {"session_id": "s2"})

    q = emb.embed(["caches"])[0]
    scoped = store.query(q, top_k=5, where={"session_id": "s1"})
    assert {h["id"] for h in scoped} == {"a"}

    store.delete_by_session("s1")
    assert {h["id"] for h in store.query(q, top_k=5)} == {"b"}


def test_query_empty_collection_returns_empty(store):
    emb = HashingEmbeddings()
    assert store.query(emb.embed(["anything"])[0]) == []
