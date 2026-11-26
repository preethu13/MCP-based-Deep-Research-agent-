"""``generate_citation`` tool (MCP-03, F-03).

Deterministic APA-7 and MLA-9 style citation strings for web sources.
Titles are wrapped in Markdown italics (``*...*``) so they render correctly in
the References section of every output format.  Missing author / publisher /
date are all handled gracefully (AC-07).
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Literal
from urllib.parse import urlparse

Style = Literal["apa", "mla"]


def _site_name(source: dict[str, Any]) -> str:
    """Publisher / site name, falling back to the URL host."""
    publisher = (source.get("venue") or source.get("publisher") or "").strip()
    if publisher and publisher.lower() not in ("venue unavailable", "unknown", "n/a"):
        return publisher
    netloc = urlparse(source.get("url", "")).netloc
    return netloc[4:] if netloc.startswith("www.") else netloc


def _format_single_author_apa(name: str) -> str:
    """Format single author string into APA style: 'Last, F. M.'"""
    name = re.sub(r"\bet al\.?$", "", name, flags=re.IGNORECASE).strip().rstrip(",")
    if not name or name.lower() in ("unknown", "authors unavailable", "authors not listed", "n/a"):
        return ""
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        last = parts[0]
        first = parts[1] if len(parts) > 1 else ""
    else:
        tokens = name.split()
        if len(tokens) == 1:
            return tokens[0]
        last = tokens[-1]
        first = " ".join(tokens[:-1])

    # Extract initials from first and middle names
    initials = [f"{m[0].upper()}." for m in re.findall(r"[A-Za-z]+", first)]
    if initials:
        return f"{last}, {' '.join(initials)}"
    return last


def format_authors_apa(source: dict[str, Any]) -> str:
    """Formats full author list in APA-7 style."""
    authors = source.get("authors")
    if isinstance(authors, list) and authors:
        cleaned = [_format_single_author_apa(a) for a in authors if _format_single_author_apa(a)]
        if not cleaned:
            return ""
        if len(cleaned) == 1:
            return cleaned[0]
        elif len(cleaned) == 2:
            return f"{cleaned[0]}, & {cleaned[1]}"
        elif len(cleaned) <= 20:
            return ", ".join(cleaned[:-1]) + f", & {cleaned[-1]}"
        else:
            return ", ".join(cleaned[:19]) + f", ... {cleaned[-1]}"

    raw_author = str(source.get("author", "")).strip()
    if not raw_author or raw_author.lower() in ("unknown", "authors unavailable", "authors not listed", "n/a"):
        return ""

    has_et_al = bool(re.search(r"\bet al\.?$", raw_author, re.IGNORECASE))
    cleaned_str = re.sub(r"\bet al\.?$", "", raw_author, flags=re.IGNORECASE).strip().rstrip(",")

    tokens = [t.strip() for t in cleaned_str.split(",") if t.strip()]
    if len(tokens) >= 2 and all(" " in t for t in tokens):
        formatted = [_format_single_author_apa(t) for t in tokens if _format_single_author_apa(t)]
        if has_et_al:
            return ", ".join(formatted) + ", et al."
        if len(formatted) == 2:
            return f"{formatted[0]}, & {formatted[1]}"
        return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"

    single = _format_single_author_apa(cleaned_str)
    if has_et_al:
        return f"{single}, et al."
    return single


def format_authors_mla(source: dict[str, Any]) -> str:
    """Formats full author list in MLA-9 style."""
    authors = source.get("authors")
    if isinstance(authors, list) and authors:
        if len(authors) == 1:
            parts = authors[0].split()
            last = parts[-1]
            first = " ".join(parts[:-1])
            return f"{last}, {first}" if first else last
        elif len(authors) == 2:
            a1_parts = authors[0].split()
            a1 = f"{a1_parts[-1]}, {' '.join(a1_parts[:-1])}" if len(a1_parts) > 1 else authors[0]
            return f"{a1}, and {authors[1]}"
        else:
            a1_parts = authors[0].split()
            a1 = f"{a1_parts[-1]}, {' '.join(a1_parts[:-1])}" if len(a1_parts) > 1 else authors[0]
            return f"{a1}, et al."

    raw = str(source.get("author", "")).strip()
    if not raw or raw.lower() in ("unknown", "authors unavailable", "authors not listed", "n/a"):
        return ""
    parts = raw.split()
    if len(parts) >= 2:
        return f"{parts[-1]}, {' '.join(parts[:-1])}"
    return raw


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
    """Generate a formatted citation string for an academic or web source.

    Args:
        source: dict with keys ``url``, ``title``, optional ``authors``/``author``,
            ``venue``/``publisher``, ``year``, ``doi``, ``publication_status``.
        style: ``"apa"`` or ``"mla"``.
        accessed_date: date the source was accessed (defaults to today).

    Returns:
        A single formatted citation string.
    """
    accessed = accessed_date or date.today()
    url = (source.get("doi") or source.get("url") or "").strip()
    title = (source.get("title") or "").strip() or "Untitled"
    site = _site_name(source)
    year = str(source.get("year")).strip() if source.get("year") else ""
    pub_status = str(source.get("publication_status", "")).strip()

    if style == "mla":
        author_mla = format_authors_mla(source)
        segments: list[str] = []
        if author_mla:
            segments.append(_ensure_period(author_mla))
        segments.append(f'"{title}."')
        if site:
            segments.append(f"*{site}*,")
        if year:
            segments.append(f"{year},")
        if url:
            segments.append(f"{url}.")
        segments.append(f"Accessed {_mla_date(accessed)}.")
        return " ".join(segments)

    # --- APA-7 (default) ---
    author_apa = format_authors_apa(source)
    segments = []
    if author_apa:
        segments.append(_ensure_period(author_apa))

    date_part = f"({year})." if year and year.lower() != "n.d." else "(n.d.)."
    segments.append(date_part)

    # For preprints (arXiv), title is in italics followed by repository name
    is_arxiv = "arxiv" in pub_status.lower() or "arxiv" in site.lower() or "arxiv" in url.lower()

    if is_arxiv:
        segments.append(f"*{title}*.")
        segments.append("arXiv.")
    elif "conference" in pub_status.lower() or "proceedings" in site.lower():
        segments.append(f"{_ensure_period(title)}")
        if site and site != "Venue unavailable":
            segments.append(f"In *{site}*.")
    elif "journal" in pub_status.lower():
        segments.append(f"{_ensure_period(title)}")
        if site and site != "Venue unavailable":
            segments.append(f"*{_ensure_period(site)}*")
    else:
        # Standard web / other publication
        segments.append(f"*{title}*.")
        if site and site != "Venue unavailable":
            segments.append(_ensure_period(site))

    if year:
        if url:
            segments.append(url)
    else:
        if url:
            segments.append(f"Retrieved {_apa_date(accessed)}, from {url}")
        else:
            segments.append(f"Retrieved {_apa_date(accessed)}")

    return " ".join(s for s in segments if s).strip()

