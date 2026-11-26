"""Embedding providers (MEM-02).

Two implementations behind a common :class:`EmbeddingProvider` protocol:

* :class:`OllamaEmbeddings` — real local embeddings via ``nomic-embed-text``.
* :class:`HashingEmbeddings` — a deterministic, dependency-free feature-hashing
  bag-of-words embedder used by the test suite and as an offline fallback.
  It is crude but genuinely lexical, so semantically related texts score higher
  cosine similarity than unrelated ones — enough to exercise recall logic in CI
  without a running Ollama server.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Protocol, runtime_checkable

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Anything that turns text into fixed-length float vectors."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


def _extract(resp: Any, key: str) -> Any:
    """Read ``key`` from an Ollama response that may be a dict or a pydantic model."""
    try:
        return resp[key]
    except (TypeError, KeyError):
        return getattr(resp, key)


class OllamaEmbeddings:
    """Local embeddings backed by an Ollama embedding model."""

    def __init__(self, model: str = "nomic-embed-text", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self._client_obj: Any = None

    def _client(self) -> Any:
        if self._client_obj is None:
            import ollama  # lazy import — keeps unit tests light

            self._client_obj = ollama.Client(host=self.host)
        return self._client_obj

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._client()

        # Prefer the batch API when the installed ollama version exposes it.
        if hasattr(client, "embed"):
            try:
                resp = client.embed(model=self.model, input=list(texts))
                embeddings = _extract(resp, "embeddings")
                return [[float(x) for x in row] for row in embeddings]
            except Exception:
                pass  # fall back to per-text calls below

        out: list[list[float]] = []
        for text in texts:
            resp = client.embeddings(model=self.model, prompt=text)
            out.append([float(x) for x in _extract(resp, "embedding")])
        return out


class HashingEmbeddings:
    """Deterministic feature-hashing bag-of-words embedder (offline / tests)."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 2]

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in self._tokens(text):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[index] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            # Empty / stop-word-only text: return a stable non-zero unit vector.
            vec[0] = 1.0
            return vec
        return [v / norm for v in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class CachedEmbeddingProvider:
    """Wraps any EmbeddingProvider with persistent hash-based batch caching."""

    def __init__(self, provider: EmbeddingProvider, cache: Any | None = None) -> None:
        self.provider = provider
        if cache is None:
            from src.memory.cache import ResearchCache

            self.cache = ResearchCache.get_instance()
        else:
            self.cache = cache

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        from src.agent.profiler import get_profiler
        from src.memory.cache import normalize_cache_key

        prof = get_profiler()
        with prof.measure_operation("embedding", count=len(texts)):
            results: list[list[float] | None] = [None] * len(texts)
            uncached_indices: list[int] = []
            uncached_texts: list[str] = []

            for i, text in enumerate(texts):
                key = normalize_cache_key(text)
                cached_vec = self.cache.get("embedding", key)
                if cached_vec is not None:
                    results[i] = cached_vec
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(text)

            if uncached_texts:
                computed_vectors = self.provider.embed(uncached_texts)
                for idx, text, vec in zip(uncached_indices, uncached_texts, computed_vectors):
                    results[idx] = vec
                    self.cache.set("embedding", normalize_cache_key(text), vec, ttl_seconds=86400 * 7)

            return [r for r in results if r is not None]
