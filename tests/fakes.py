"""Reusable offline fakes shared by conftest fixtures and integration tests."""

from __future__ import annotations

import json
from typing import Any

from src.agent.llm import loads_lenient
from src.memory.embeddings import cosine_similarity


class FakeVectorStore:
    """In-memory stand-in for :class:`src.memory.vector_store.VectorStore`."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[str, list[float], dict[str, Any]]] = {}

    def add(self, vector_id, text, embedding, metadata=None):
        self._items[vector_id] = (text, list(embedding), dict(metadata or {}))

    def query(self, embedding, top_k=5, where=None):
        hits = []
        for vid, (text, emb, meta) in self._items.items():
            if where and not all(meta.get(k) == v for k, v in where.items()):
                continue
            sim = cosine_similarity(embedding, emb)
            hits.append(
                {
                    "id": vid,
                    "text": text,
                    "metadata": meta,
                    "distance": 1.0 - sim,
                    "similarity": max(0.0, min(1.0, sim)),
                }
            )
        hits.sort(key=lambda h: h["similarity"], reverse=True)
        return hits[:top_k]

    def count(self):
        return len(self._items)

    def delete_by_session(self, session_id):
        self._items = {
            k: v for k, v in self._items.items() if v[2].get("session_id") != session_id
        }

    def reset(self):
        self._items = {}


class FakeLLM:
    """Deterministic LLM returning valid output for every node prompt."""

    def __init__(self, sub_questions: list[str] | None = None):
        self.sub_questions = sub_questions or ["What is Redis?", "What is Memcached?"]
        self.calls: list[str] = []

    def complete(self, system: str, user: str, *args: Any, **kwargs: Any) -> str:
        s = system.lower()
        self.calls.append(s[:40])
        if "convert research notes" in s or "structured comparison" in s:
            return json.dumps(
                {
                    "dimensions": ["Overview", "Best for"],
                    "entities": [
                        {"name": "Redis", "attributes": {"Overview": "in-memory store", "Best for": "rich types"}},
                        {"name": "Memcached", "attributes": {"Overview": "cache", "Best for": "simple KV"}},
                    ],
                }
            )
        if "research analyst" in s:
            return "A grounded claim synthesised strictly from the provided sources."
        return json.dumps(self.sub_questions)

    def complete_json(self, system: str, user: str, *args: Any, **kwargs: Any) -> Any:
        return loads_lenient(self.complete(system, user, *args, **kwargs))

    def ping(self) -> tuple[bool, str]:
        return True, "fake llm"
