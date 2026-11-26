"""Performance profiler and operational metrics tracker (latency, counts, tokens)."""
from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("research.profiler")


class Profiler:
    """Thread-safe latency and operation profiler for the Deep Research Agent."""

    _instance: Profiler | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._node_timings: dict[str, float] = {}
        self._node_start: dict[str, float] = {}
        self._op_counts: dict[str, int] = {}
        self._op_durations: dict[str, float] = {}
        self._token_usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self._run_start: float = time.perf_counter()
        self._active_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> Profiler:
        with cls._lock:
            if cls._instance is None:
                cls._instance = Profiler()
            return cls._instance

    @classmethod
    def reset(cls) -> Profiler:
        with cls._lock:
            inst = cls.get_instance()
            with inst._active_lock:
                inst._node_timings.clear()
                inst._node_start.clear()
                inst._op_counts.clear()
                inst._op_durations.clear()
                inst._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                inst._run_start = time.perf_counter()
            return inst

    def start_node(self, node_name: str) -> None:
        with self._active_lock:
            self._node_start[node_name] = time.perf_counter()

    def end_node(self, node_name: str) -> float:
        with self._active_lock:
            start = self._node_start.get(node_name, time.perf_counter())
            duration = round(time.perf_counter() - start, 4)
            self._node_timings[node_name] = duration
            return duration

    @contextmanager
    def measure_node(self, node_name: str):
        self.start_node(node_name)
        try:
            yield
        finally:
            self.end_node(node_name)

    @contextmanager
    def measure_operation(self, op_name: str, count: int = 1):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            dur = time.perf_counter() - t0
            self.record_op(op_name, dur, count)

    def record_op(self, op_name: str, duration: float, count: int = 1) -> None:
        with self._active_lock:
            self._op_counts[op_name] = self._op_counts.get(op_name, 0) + count
            self._op_durations[op_name] = round(self._op_durations.get(op_name, 0.0) + duration, 4)

    def record_tokens(self, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        with self._active_lock:
            self._token_usage["prompt_tokens"] += prompt_tokens
            self._token_usage["completion_tokens"] += completion_tokens
            self._token_usage["total_tokens"] += (prompt_tokens + completion_tokens)

    def get_metrics(self) -> dict[str, Any]:
        with self._active_lock:
            total_wall_clock = round(time.perf_counter() - self._run_start, 4)
            return {
                "total_duration_seconds": total_wall_clock,
                "node_latencies": dict(self._node_timings),
                "operation_counts": dict(self._op_counts),
                "operation_durations": dict(self._op_durations),
                "tokens": dict(self._token_usage),
            }

    def log_summary(self) -> None:
        metrics = self.get_metrics()
        logger.info(
            "Agent Execution Profile | Total: %.2fs | Nodes: %s | Operations: %s | Tokens: %s",
            metrics["total_duration_seconds"],
            metrics["node_latencies"],
            metrics["operation_counts"],
            metrics["tokens"],
        )


def get_profiler() -> Profiler:
    return Profiler.get_instance()
