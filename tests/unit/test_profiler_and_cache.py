"""Unit tests for profiling, caching, and batch embedding optimizations."""
from __future__ import annotations

import time
from src.agent.profiler import Profiler, get_profiler
from src.memory.cache import ResearchCache, normalize_cache_key
from src.memory.embeddings import CachedEmbeddingProvider, HashingEmbeddings


def test_profiler_records_timings_and_tokens():
    prof = Profiler.reset()
    prof.start_node("planner")
    time.sleep(0.01)
    dur = prof.end_node("planner")
    assert dur > 0

    with prof.measure_operation("test_op", count=2):
        time.sleep(0.01)

    prof.record_tokens(prompt_tokens=100, completion_tokens=50)

    metrics = prof.get_metrics()
    assert "planner" in metrics["node_latencies"]
    assert metrics["operation_counts"].get("test_op") == 2
    assert metrics["tokens"]["prompt_tokens"] == 100
    assert metrics["tokens"]["completion_tokens"] == 50
    assert metrics["tokens"]["total_tokens"] == 150


def test_research_cache_in_memory_and_sqlite(tmp_path):
    db_file = tmp_path / "test_cache.db"
    cache = ResearchCache(db_path=db_file, default_ttl_seconds=60)

    # Set and get
    cache.set("search", "query_1", {"results": [1, 2, 3]})
    val = cache.get("search", "query_1")
    assert val == {"results": [1, 2, 3]}

    # Different key miss
    assert cache.get("search", "query_2") is None

    # Expiration
    cache.set("search", "expiring_key", "data", ttl_seconds=0.01)
    time.sleep(0.02)
    assert cache.get("search", "expiring_key") is None


def test_normalize_cache_key():
    k1 = normalize_cache_key("Context Rot in LLMs  ")
    k2 = normalize_cache_key("context  rot in llms")
    assert k1 == k2


def test_cached_embedding_provider(tmp_path):
    db_file = tmp_path / "emb_cache.db"
    cache = ResearchCache(db_path=db_file)
    base_embedder = HashingEmbeddings(dim=64)
    cached_embedder = CachedEmbeddingProvider(base_embedder, cache=cache)

    texts = ["apple", "banana", "apple"]
    vecs1 = cached_embedder.embed(texts)
    assert len(vecs1) == 3
    assert vecs1[0] == vecs1[2]

    # Second call should fetch directly from cache with zero computation
    vecs2 = cached_embedder.embed(["apple"])
    assert vecs2[0] == vecs1[0]
