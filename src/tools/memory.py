"""``store_memory`` and ``recall_memory`` tools (MCP-04, MCP-05).

These orchestrate the embedding provider, the ChromaDB vector store and the
SQLite pointer table.  Dependencies are injected so the tools are fully unit
testable with a fake embedder and temp stores (no Ollama, no network).
"""

from __future__ import annotations

import uuid
from typing import Any

from src.memory.embeddings import EmbeddingProvider
from src.memory.sqlite_store import SQLiteStore
from src.memory.vector_store import VectorStore, VectorStoreError


def store_memory(
    session_id: str,
    content: str,
    metadata: dict[str, Any],
    *,
    vector_store: VectorStore,
    sqlite_store: SQLiteStore | None = None,
    embeddings: EmbeddingProvider,
) -> dict[str, Any]:
    """Embed and persist a piece of research content for future recall.

    Returns a dict confirming storage with the generated vector ID, or an
    ``error`` key if the vector backend is unavailable (SQLite-only degrade).
    """
    if not content.strip():
        return {"status": "skipped", "reason": "empty content"}

    vector_id = f"{session_id}:{uuid.uuid4().hex}"
    meta = {**(metadata or {}), "session_id": session_id}

    try:
        vector = embeddings.embed([content])[0]
        vector_store.add(vector_id, content, vector, meta)
    except VectorStoreError as exc:
        return {"status": "error", "reason": str(exc), "vector_id": None}
    except Exception as exc:  # embedding failure (e.g. Ollama down)
        return {"status": "error", "reason": f"embedding failed: {exc}", "vector_id": None}

    if sqlite_store is not None:
        try:
            sqlite_store.add_memory_pointer(session_id, vector_id, content[:500])
        except Exception:
            # Session row may not exist in isolated use; pointer is best-effort.
            pass

    return {"status": "stored", "vector_id": vector_id}


def recall_memory(
    session_id: str,
    query: str,
    top_k: int = 5,
    *,
    vector_store: VectorStore,
    embeddings: EmbeddingProvider,
    threshold: float = 0.75,
) -> list[dict[str, Any]]:
    """Retrieve semantically relevant past findings for ``query``.

    ``session_id='all'`` searches across every session (cross-session recall,
    AC-09).  Only hits at or above the cosine-similarity ``threshold`` (MEM-03)
    are returned, ranked most-similar first.
    """
    if not query.strip():
        return []

    where = None if session_id in (None, "all", "") else {"session_id": session_id}

    try:
        vector = embeddings.embed([query])[0]
        hits = vector_store.query(vector, top_k=top_k, where=where)
    except VectorStoreError:
        return []  # graceful degradation: no semantic recall available
    except Exception:
        return []

    relevant = [h for h in hits if h["similarity"] >= threshold]
    return [
        {
            "content": h["text"],
            "similarity_score": round(h["similarity"], 4),
            "session_id": h["metadata"].get("session_id", "unknown"),
            "metadata": h["metadata"],
        }
        for h in relevant
    ]
