"""Unit tests for embedding providers and cosine similarity."""

from __future__ import annotations

import math

from src.memory.embeddings import HashingEmbeddings, cosine_similarity


def test_hashing_is_deterministic():
    emb = HashingEmbeddings()
    a = emb.embed(["redis in-memory cache"])[0]
    b = emb.embed(["redis in-memory cache"])[0]
    assert a == b


def test_hashing_vectors_are_unit_length():
    emb = HashingEmbeddings(dim=128)
    vec = emb.embed(["some meaningful words here"])[0]
    assert len(vec) == 128
    assert math.isclose(math.sqrt(sum(v * v for v in vec)), 1.0, rel_tol=1e-6)


def test_related_text_scores_higher_than_unrelated():
    emb = HashingEmbeddings()
    query = emb.embed(["redis in-memory key value store caching"])[0]
    related = emb.embed(["redis is an in-memory key value store used for caching"])[0]
    unrelated = emb.embed(["photosynthesis converts sunlight into chemical energy"])[0]
    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)


def test_empty_text_gives_stable_nonzero_vector():
    emb = HashingEmbeddings()
    vec = emb.embed([""])[0]
    assert any(v != 0.0 for v in vec)


def test_cosine_similarity_edges():
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0
    assert math.isclose(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)
