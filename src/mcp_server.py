"""FastMCP tool server (F-01, MCP-01..09).

Exposes the research capabilities as Model Context Protocol tools.  Each tool:

* returns structured, JSON-serialisable data and never propagates a raw
  exception (MCP-07);
* is timed and logged to the local log file (MCP-08);
* runs under a per-tool timeout — 10 s search, 30 s scrape (MCP-09).

Run standalone for any MCP client (e.g. Claude Desktop)::

    python -m src.mcp_server

The LangGraph agent reuses these same tools in-process (see
``src/agent/tool_client.py``) so behaviour is identical whether driven over the
MCP transport or embedded.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Any, Callable, Literal

from fastmcp import FastMCP

from src.config import get_settings
from src.logging_utils import get_logger
from src.memory.embeddings import OllamaEmbeddings
from src.memory.sqlite_store import SQLiteStore
from src.memory.vector_store import VectorStore
from src.tools.citation import generate_citation as _generate_citation
from src.tools.formatter import format_output as _format_output
from src.tools.memory import recall_memory as _recall_memory
from src.tools.memory import store_memory as _store_memory
from src.tools.scrape import scrape_page as _scrape_page
from src.tools.search import search_academic_papers as _search_academic_papers
from src.tools.search import web_search as _web_search

settings = get_settings()
logger = get_logger("mcp", settings.log_file)

mcp = FastMCP("deep-research-agent")

# --- shared, lazily-backed singletons ---
_embeddings = OllamaEmbeddings(settings.embed_model, settings.ollama_host)
_sqlite = SQLiteStore(settings.db_path)
_sqlite.initialize()
_vector = VectorStore(settings.chroma_dir)

_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="mcp-tool")


def _run(tool: str, seconds: int, fn: Callable, on_error: Callable[[str], Any], **kwargs) -> Any:
    """Time, log, timeout-guard and exception-guard a tool call (MCP-07/08/09)."""
    start = time.perf_counter()
    try:
        future = _executor.submit(fn, **kwargs)
        result = future.result(timeout=seconds)
        logger.info("tool=%s status=ok duration_ms=%.1f", tool, (time.perf_counter() - start) * 1000)
        return result
    except FuturesTimeout:
        logger.error("tool=%s status=timeout limit_s=%d", tool, seconds)
        return on_error(f"timed out after {seconds}s")
    except Exception as exc:  # final safety net — never raise to the client
        logger.error("tool=%s status=error error=%s", tool, exc)
        return on_error(str(exc))


# ─────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────
@mcp.tool()
def search_academic_papers(query: str, max_results: int = 5) -> list[dict]:
    """Search for academic research papers and preprints via OpenAlex.

    Args:
        query: The academic search topic or question.
        max_results: Maximum number of papers to return (default 5).

    Returns:
        List of paper metadata dicts (title, authors, year, venue, url, abstract).
    """
    return _run(
        "search_academic_papers",
        settings.search_timeout,
        _search_academic_papers,
        on_error=lambda _msg: [],
        query=query,
        max_results=max_results,
        timeout=settings.search_timeout,
    )


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web via DuckDuckGo (no API key required).

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 5).

    Returns:
        A list of dicts each with ``title``, ``url`` and ``snippet``.
    """
    return _run(
        "web_search",
        settings.search_timeout,
        _web_search,
        on_error=lambda _msg: [],
        query=query,
        max_results=max_results,
        timeout=settings.search_timeout,
    )


@mcp.tool()
def scrape_page(url: str) -> dict:
    """Fetch and extract clean text content from a web page.

    Falls back to Playwright rendering if static extraction yields less than
    200 characters of usable text.

    Args:
        url: The full URL to scrape.

    Returns:
        dict with keys ``url``, ``title``, ``text``, ``word_count``, ``method_used``.
    """
    return _run(
        "scrape_page",
        settings.scrape_timeout,
        _scrape_page,
        on_error=lambda msg: {
            "url": url,
            "title": "",
            "text": "",
            "word_count": 0,
            "method_used": "failed",
            "error": msg,
        },
        url=url,
        timeout=settings.scrape_timeout,
        user_agent=settings.user_agent,
        respect_robots=settings.respect_robots_txt,
    )


@mcp.tool()
def generate_citation(source: dict, style: Literal["apa", "mla"] = "apa") -> str:
    """Generate a formatted citation string for a given source.

    Args:
        source: dict with keys ``url``, ``title``, optional ``author``/``publisher``/``year``.
        style: Citation style, either ``'apa'`` or ``'mla'``.

    Returns:
        A formatted citation string.
    """
    return _run(
        "generate_citation",
        settings.search_timeout,
        _generate_citation,
        on_error=lambda msg: f"[citation unavailable: {msg}]",
        source=source,
        style=style,
    )


@mcp.tool()
def store_memory(session_id: str, content: str, metadata: dict) -> dict:
    """Embed and persist a piece of research content for future recall.

    Args:
        session_id: Identifier of the current research session.
        content: The text content to remember.
        metadata: Arbitrary metadata (topic, source_url, etc).

    Returns:
        dict confirming storage with the generated vector ID.
    """
    return _run(
        "store_memory",
        settings.scrape_timeout,
        _store_memory,
        on_error=lambda msg: {"status": "error", "reason": msg, "vector_id": None},
        session_id=session_id,
        content=content,
        metadata=metadata,
        vector_store=_vector,
        sqlite_store=_sqlite,
        embeddings=_embeddings,
    )


@mcp.tool()
def recall_memory(session_id: str, query: str, top_k: int = 5) -> list[dict]:
    """Retrieve semantically relevant past findings for a query.

    Args:
        session_id: Session to scope recall to (or ``'all'`` for global recall).
        query: The text to find semantically similar memories for.
        top_k: Number of results to return.

    Returns:
        A list of dicts with ``content``, ``similarity_score`` and ``session_id``.
    """
    return _run(
        "recall_memory",
        settings.scrape_timeout,
        _recall_memory,
        on_error=lambda _msg: [],
        session_id=session_id,
        query=query,
        top_k=top_k,
        vector_store=_vector,
        embeddings=_embeddings,
        threshold=settings.memory_relevance_threshold,
    )


@mcp.tool()
def format_output(findings: list[dict], format: Literal["brief", "comparison", "report"]) -> str:
    """Render findings into one of three output formats.

    Args:
        findings: List of finding dicts (claim, citations, sub_question).
        format: One of ``'brief'``, ``'comparison'`` or ``'report'``.

    Returns:
        A fully formatted Markdown string ready for export.
    """
    return _run(
        "format_output",
        settings.search_timeout,
        _format_output,
        on_error=lambda msg: f"# Output error\n\n{msg}\n",
        findings=findings,
        format=format,
    )


def main() -> None:
    """Entry point for ``python -m src.mcp_server``."""
    logger.info("Starting FastMCP server 'deep-research-agent' (stdio transport)")
    mcp.run()


if __name__ == "__main__":
    main()
