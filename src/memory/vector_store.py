"""ChromaDB vector memory store (MEM-02, MEM-03).

Wraps a local, embedded, persistent Chroma collection configured for cosine
distance.  Embeddings are computed *outside* Chroma (by our Ollama / hashing
provider) and passed in explicitly, so Chroma never downloads its own model and
everything stays fully local and offline-capable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class VectorStoreError(RuntimeError):
    """Raised when the vector backend is unavailable or corrupt."""


def _sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Chroma only accepts str/int/float/bool scalar metadata values."""
    clean: dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            clean[key] = value
        else:
            clean[key] = str(value)
    return clean


class VectorStore:
    """Semantic memory backed by a persistent ChromaDB collection."""

    def __init__(
        self,
        chroma_dir: str | Path = "data/chroma",
        collection_name: str = "research_memories",
    ):
        self.chroma_dir = Path(chroma_dir)
        self.collection_name = collection_name
        self._collection: Any = None

    def _get_collection(self) -> Any:
        if self._collection is not None:
            return self._collection
        try:
            import chromadb  # lazy import — heavy dependency

            self.chroma_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.chroma_dir))
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            return self._collection
        except Exception as exc:  # pragma: no cover - depends on environment
            raise VectorStoreError(f"ChromaDB unavailable: {exc}") from exc

    def add(
        self,
        vector_id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        collection = self._get_collection()
        add_fn = getattr(collection, "upsert", getattr(collection, "add", None))
        if callable(add_fn):
            add_fn(
                ids=[vector_id],
                documents=[text],
                embeddings=[embedding],
                metadatas=[_sanitize_metadata(metadata)],
            )

    def query(
        self,
        embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Return the ``top_k`` most similar memories as ranked dicts.

        Each dict carries ``id``, ``text``, ``metadata``, ``distance`` and a
        derived cosine ``similarity`` in ``[0, 1]`` (``1`` == identical).
        """
        collection = self._get_collection()
        if self.count() == 0:
            return []
        result = collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where or None,
            include=["documents", "metadatas", "distances"],
        )

        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]

        hits: list[dict[str, Any]] = []
        for i, vid in enumerate(ids):
            distance = float(dists[i]) if i < len(dists) else 1.0
            similarity = max(0.0, min(1.0, 1.0 - distance))
            hits.append(
                {
                    "id": vid,
                    "text": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": distance,
                    "similarity": similarity,
                }
            )
        return hits

    def count(self) -> int:
        try:
            return int(self._get_collection().count())
        except VectorStoreError:
            raise
        except Exception:  # pragma: no cover
            return 0

    def delete_by_session(self, session_id: str) -> None:
        collection = self._get_collection()
        collection.delete(where={"session_id": session_id})

    def reset(self) -> None:
        """Drop and recreate the collection (used by tests)."""
        collection = self._get_collection()
        ids = collection.get().get("ids", [])
        if ids:
            collection.delete(ids=ids)
