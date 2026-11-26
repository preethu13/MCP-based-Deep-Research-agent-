"""Multi-tier persistent and in-memory cache for search, scrape, and embeddings."""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable

from src.agent.profiler import get_profiler

logger = logging.getLogger("research.cache")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache_store (
    category     TEXT NOT NULL,
    cache_key    TEXT NOT NULL,
    data_json    TEXT NOT NULL,
    created_at   REAL NOT NULL,
    expires_at   REAL NOT NULL,
    PRIMARY KEY (category, cache_key)
);
CREATE INDEX IF NOT EXISTS idx_cache_lookup ON cache_store(category, cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_store(expires_at);
"""


class ResearchCache:
    """Thread-safe two-tier cache with in-memory LRU and SQLite backing."""

    _instance: ResearchCache | None = None
    _lock = threading.Lock()

    def __init__(
        self,
        db_path: str | Path = "data/research.db",
        default_ttl_seconds: float = 86400.0,  # 24 hours
        max_memory_items: int = 500,
    ) -> None:
        self.db_path = Path(db_path)
        self.default_ttl = default_ttl_seconds
        self.max_memory_items = max_memory_items
        self._mem_cache: OrderedDict[tuple[str, str], tuple[float, Any]] = OrderedDict()
        self._cache_lock = threading.Lock()

        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: str | Path = "data/research.db") -> ResearchCache:
        with cls._lock:
            if cls._instance is None:
                cls._instance = ResearchCache(db_path=db_path)
            return cls._instance

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA busy_timeout = 5000;")
                conn.executescript(_SCHEMA)
        except Exception as exc:
            logger.warning("Failed to initialize SQLite cache: %s", exc)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, category: str, key: str) -> Any | None:
        """Lookup an unexpired item by category and key."""
        now = time.time()
        prof = get_profiler()

        # 1. Check in-memory LRU cache
        with self._cache_lock:
            mem_item = self._mem_cache.get((category, key))
            if mem_item:
                expires_at, val = mem_item
                if expires_at > now:
                    self._mem_cache.move_to_end((category, key))
                    prof.record_op("cache_hit", 0.0001)
                    return val
                else:
                    del self._mem_cache[(category, key)]

        # 2. Check persistent SQLite cache
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT data_json, expires_at FROM cache_store WHERE category = ? AND cache_key = ?",
                    (category, key),
                ).fetchone()
                if row:
                    expires_at = float(row["expires_at"])
                    if expires_at > now:
                        data = json.loads(row["data_json"])
                        # Populate in-memory LRU
                        with self._cache_lock:
                            self._mem_cache[(category, key)] = (expires_at, data)
                            if len(self._mem_cache) > self.max_memory_items:
                                self._mem_cache.popitem(last=False)
                        prof.record_op("cache_hit", 0.0005)
                        return data
                    else:
                        # Expired entry - clean up asynchronously
                        conn.execute(
                            "DELETE FROM cache_store WHERE category = ? AND cache_key = ?",
                            (category, key),
                        )
        except Exception as exc:
            logger.debug("Cache read exception: %s", exc)

        prof.record_op("cache_miss", 0.0001)
        return None

    def set(
        self,
        category: str,
        key: str,
        value: Any,
        ttl_seconds: float | None = None,
    ) -> None:
        """Store an item in both in-memory LRU and SQLite."""
        now = time.time()
        ttl = self.default_ttl if ttl_seconds is None else ttl_seconds
        expires_at = now + ttl

        # 1. Update in-memory LRU
        with self._cache_lock:
            self._mem_cache[(category, key)] = (expires_at, value)
            self._mem_cache.move_to_end((category, key))
            if len(self._mem_cache) > self.max_memory_items:
                self._mem_cache.popitem(last=False)

        # 2. Persist to SQLite
        try:
            val_json = json.dumps(value)
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO cache_store (category, cache_key, data_json, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(category, cache_key) DO UPDATE SET
                        data_json = excluded.data_json,
                        created_at = excluded.created_at,
                        expires_at = excluded.expires_at
                    """,
                    (category, key, val_json, now, expires_at),
                )
        except Exception as exc:
            logger.debug("Cache write exception: %s", exc)

    def get_or_compute(
        self,
        category: str,
        key: str,
        compute_fn: Callable[[], Any],
        ttl_seconds: float | None = None,
    ) -> Any:
        cached = self.get(category, key)
        if cached is not None:
            return cached
        computed = compute_fn()
        if computed is not None:
            self.set(category, key, computed, ttl_seconds=ttl_seconds)
        return computed

    def clear(self) -> None:
        with self._cache_lock:
            self._mem_cache.clear()
        try:
            with self._connect() as conn:
                conn.execute("DELETE FROM cache_store")
        except Exception:
            pass


def normalize_cache_key(text: str) -> str:
    """Deterministically hash/normalize arbitrary search or document text."""
    clean = " ".join(text.strip().lower().split())
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()
