"""``generate_citation`` tool (MCP-03, F-03).

Deterministic APA-7 and MLA-9 style citation strings for web sources.
Titles are wrapped in Markdown italics (``*...*``) so they render correctly in
the References section of every output format.  Missing author / publisher /
date are all handled gracefully (AC-07).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal
from urllib.parse import urlparse

Style = Literal["apa", "mla"]


def _site_name(source: dict[str, Any]) -> str:
    """Publisher / site name, falling back to the URL host."""
    publisher = (source.get("publisher") or "").strip()
    if publisher:
        return publisher
    netloc = urlparse(source.get("url", "")).netloc
    return netloc[4:] if netloc.startswith("www.") else netloc


def _split_name(author: str) -> tuple[str, str] | None:
    """Split "First [Middle] Last" -> (first_middle, last). None if single token."""
    parts = author.split()
    if len(parts) < 2:
        return None
    return " ".join(parts[:-1]), parts[-1]


def _author_apa(author: str) -> str:
    """APA author: ``Last, F. M.`` — no trailing period (caller adds it)."""
    split = _split_name(author)
    if split is None:
        return author
    first_middle, last = split
    initials = " ".join(f"{p[0]}." for p in first_middle.split() if p)
    return f"{last}, {initials}"


def _author_mla(author: str) -> str:
    """MLA author: ``Last, First Middle`` — no trailing period (caller adds it)."""
    split = _split_name(author)
    if split is None:
        return author
    first_middle, last = split
    return f"{last}, {first_middle}"


def _apa_date(d: date) -> str:
    return d.strftime("%B %d, %Y").replace(" 0", " ")


def _mla_date(d: date) -> str:
    return d.strftime("%d %B %Y").lstrip("0")


def _ensure_period(s: str) -> str:
    """Append a period to ``s`` unless it already ends with one."""
    return s if s.endswith(".") else f"{s}."


def generate_citation(
    source: dict[str, Any],
    style: Style = "apa",
    accessed_date: date | None = None,
) -> str:
    """Generate a formatted citation string for a web source.

    Args:
        source: dict with keys ``url``, ``title`` and optional ``author``,
            ``publisher``, ``year``.
        style: ``"apa"`` or ``"mla"``.
        accessed_date: date the source was accessed (defaults to today).

    Returns:
        A single formatted citation string.
    """
    accessed = accessed_date or date.today()
    url = source.get("url", "").strip()
    title = (source.get("title") or "").strip() or "Untitled"
    author = (source.get("author") or "").strip()
    site = _site_name(source)
    year = str(source.get("year")).strip() if source.get("year") else ""

    if style == "mla":
        segments: list[str] = []
        if author:
            segments.append(_ensure_period(_author_mla(author)))
        segments.append(f'"{title}."')
        if site:
            segments.append(f"*{site}*,")
        if year:
            segments.append(f"{year},")
        segments.append(f"{url}.")
        segments.append(f"Accessed {_mla_date(accessed)}.")
        return " ".join(segments)

    # --- APA (default) ---
    # _author_apa() returns e.g. "Doe, J." — the trailing period is part of the
    # last initial, so we must NOT append another dot.
    segments = []
    if author:
        segments.append(_ensure_period(_author_apa(author)))
    date_part = f"({year})." if year else "(n.d.)."
    segments.append(date_part)
    segments.append(f"*{title}*.")
    if site:
        segments.append(_ensure_period(site))
    if year:
        segments.append(url)
    else:
        # APA: include a retrieval date for undated online material.
        segments.append(f"Retrieved {_apa_date(accessed)}, from {url}")
    return " ".join(s for s in segments if s).strip()

