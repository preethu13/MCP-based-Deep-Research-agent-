"""Structured logging for tool invocations (MCP-08).

Every tool call is recorded with its name, truncated args, wall-clock
duration and success/failure — to a rotating local log file and, at WARNING+,
to stderr.  No telemetry ever leaves the machine.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from contextlib import contextmanager
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

_CONFIGURED: set[str] = set()


def get_logger(name: str = "research", log_file: Path | str | None = None) -> logging.Logger:
    """Return a logger that writes to ``log_file`` (and stderr at WARNING+)."""
    logger = logging.getLogger(name)
    if name in _CONFIGURED:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            path, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    stream.setLevel(logging.WARNING)
    logger.addHandler(stream)

    _CONFIGURED.add(name)
    return logger


def _truncate(value: Any, limit: int = 200) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[:limit] + "…"


@contextmanager
def log_call(logger: logging.Logger, tool: str, **args: Any):
    """Context manager timing a tool call and logging the outcome."""
    start = time.perf_counter()
    arg_preview = {k: _truncate(v) for k, v in args.items()}
    try:
        yield
    except Exception as exc:  # pragma: no cover - re-raised, logging only
        duration = (time.perf_counter() - start) * 1000
        logger.error(
            "tool=%s status=error duration_ms=%.1f args=%s error=%s",
            tool,
            duration,
            json.dumps(arg_preview, default=str),
            exc,
        )
        raise
    else:
        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "tool=%s status=ok duration_ms=%.1f args=%s",
            tool,
            duration,
            json.dumps(arg_preview, default=str),
        )


def logged_tool(logger: logging.Logger, tool_name: str | None = None) -> Callable:
    """Decorator recording every invocation of a tool function."""

    def decorator(func: Callable) -> Callable:
        name = tool_name or func.__name__

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with log_call(logger, name, args=args, kwargs=kwargs):
                return func(*args, **kwargs)

        return wrapper

    return decorator
