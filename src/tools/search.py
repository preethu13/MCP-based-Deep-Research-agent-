"""``web_search`` tool (MCP-01).

Query-to-URL retrieval via DuckDuckGo, which needs no API key.  The package was
renamed ``duckduckgo_search`` -> ``ddgs`` across versions, so both imports are
tried.  The tool never raises: on any failure it returns an empty list and logs
the cause, letting the agent degrade gracefully (AG-07).
"""

from __future__ import annotations

from typing import Any

# The package was renamed duckduckgo_search -> ddgs; try the new name first.
try:  # pragma: no cover - import shim
    from ddgs import DDGS
except ImportError:  # pragma: no cover
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None  # type: ignore[assignment]


def web_search(query: str, max_results: int = 5, timeout: int = 10) -> list[dict[str, Any]]:
    """Search the web via DuckDuckGo.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
        timeout: Network timeout in seconds.

    Returns:
        A list of ``{"title", "url", "snippet"}`` dicts (possibly empty).
    """
    if DDGS is None or not query.strip():
        return []

    try:
        results: list[dict[str, Any]] = []
        with DDGS(timeout=timeout) as ddgs:
            for hit in ddgs.text(query, max_results=max_results) or []:
                url = hit.get("href") or hit.get("url") or ""
                if not url:
                    continue
                results.append(
                    {
                        "title": (hit.get("title") or "").strip() or url,
                        "url": url,
                        "snippet": (hit.get("body") or hit.get("snippet") or "").strip(),
                    }
                )
            return results[:max_results]
    except Exception:
        # Network error, rate-limit, endpoint change (FC-08) — degrade to zero results.
        return []
