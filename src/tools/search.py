"""``web_search`` and ``search_academic_papers`` tools (MCP-01).

Query-to-URL retrieval via DuckDuckGo and OpenAlex Academic Index.
No API keys required. Free, open, and fast.
The tools never raise: on any failure they return an empty list and degrade gracefully.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Any

# The package was renamed duckduckgo_search -> ddgs; try the new name first.
try:  # pragma: no cover - import shim
    from ddgs import DDGS
except ImportError:  # pragma: no cover
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None  # type: ignore[assignment]


def clean_search_query(sub_q: str, main_query: str = "") -> str:
    """Extracts concise, targeted search keywords from conversational sub-questions."""
    stopwords = {
        "what", "how", "why", "when", "where", "which", "who", "whom", "whose",
        "is", "are", "was", "were", "be", "been", "being",
        "do", "does", "did", "have", "has", "had", "having",
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "by", "about",
        "potential", "primary", "current", "real-world", "real", "world", "key",
        "causes", "mechanisms", "consequences", "strategies", "methods", "approaches", "mitigate"
    }
    words = re.findall(r"[A-Za-z0-9_-]+", sub_q)
    filtered = [w for w in words if w.lower() not in stopwords]

    main_words = re.findall(r"[A-Za-z0-9_-]+", main_query) if main_query else []
    main_keywords = [
        w for w in main_words
        if w.lower() not in {"in", "on", "at", "the", "a", "an", "of", "for", "with", "by", "to", "and", "or", "is", "are"}
    ]

    combined = []
    seen = set()
    for w in main_keywords + filtered:
        wl = w.lower()
        if wl not in seen:
            seen.add(wl)
            combined.append(w)

    return " ".join(combined[:6]) if combined else sub_q


def score_paper_relevance(paper: dict[str, Any], root_query: str) -> float:
    """Scores paper relevance against the user's research topic.

    Higher is better. Negative or low scores indicate irrelevant/off-topic papers.
    """
    stopwords = {
        "in", "on", "at", "the", "a", "an", "of", "for", "with", "by", "to", "and", "or", "is", "are",
        "what", "how", "why", "who", "when", "which",
    }
    q_words = [w.lower() for w in re.findall(r"[A-Za-z0-9_-]+", root_query) if w.lower() not in stopwords]
    if not q_words:
        return 1.0

    title = (paper.get("title") or "").lower()
    abstract = (paper.get("abstract") or "").lower()

    score = 0.0

    # 1. Exact phrase match in title (massive boost) or abstract
    clean_q = " ".join(q_words)
    if clean_q in title:
        score += 10.0
    elif clean_q in abstract:
        score += 5.0

    # 2. Check individual key words
    matched_title_words = sum(1 for w in q_words if re.search(r"\b" + re.escape(w) + r"\b", title))
    matched_abs_words = sum(1 for w in q_words if re.search(r"\b" + re.escape(w) + r"\b", abstract))

    score += matched_title_words * 3.0
    score += matched_abs_words * 1.0

    # 3. Off-topic false-friend check (e.g. Concept-ROT acronym when query is context rot)
    if "context" in q_words and "rot" in q_words:
        has_context_signal = (
            "context" in title or "context" in abstract or "long-context" in title or "long-context" in abstract
        )
        if not has_context_signal:
            score -= 10.0

    # 4. Filter unrelated domains (e.g. stock investing, financial bias) if query did not mention them
    irrelevant_domains = {"investing", "stock market", "portfolio", "equity", "financial markets", "real estate"}
    if not any(w in root_query.lower() for w in irrelevant_domains):
        if any(w in title for w in irrelevant_domains):
            score -= 15.0

    return score


def search_academic_papers(query: str, max_results: int = 5, timeout: int = 6) -> list[dict[str, Any]]:
    """Search for peer-reviewed academic papers and scientific preprints via OpenAlex.

    Returns structured dictionaries containing:
        - title: Paper title
        - url: Direct paper / DOI landing URL
        - pdf_url: Open access direct PDF URL (if available)
        - authors: List of author names
        - author_str: Formatted author string
        - year: Publication year
        - venue: Journal or conference venue
        - abstract: Full paper abstract
        - snippet: Concise excerpt
        - is_paper: True
    """
    clean_q = query.strip()
    if not clean_q:
        return []

    try:
        encoded = urllib.parse.quote_plus(clean_q)
        url = f"https://api.openalex.org/works?search={encoded}&per-page={max(1, max_results)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "DeepResearchAgent/1.0 (mailto:researcher@local.ai)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        papers: list[dict[str, Any]] = []
        for item in data.get("results", []):
            title = item.get("title")
            if not title:
                continue

            doi = item.get("doi")
            primary_loc = item.get("primary_location") or {}
            landing_url = (
                primary_loc.get("landing_page_url")
                or doi
                or (item.get("open_access") or {}).get("oa_url")
                or (f"https://doi.org/{doi}" if doi else "")
            )
            pdf_url = (primary_loc.get("pdf_url") or "") or ((item.get("open_access") or {}).get("oa_url") or "")

            authors = [
                a.get("author", {}).get("display_name")
                for a in item.get("authorships", [])
                if a.get("author", {}).get("display_name")
            ]
            year = item.get("publication_year")
            venue = (primary_loc.get("source") or {}).get("display_name") or ""

            # Reconstruct abstract from inverted index if present
            inv = item.get("abstract_inverted_index")
            abstract = ""
            if inv:
                word_pos: list[tuple[int, str]] = []
                for word, positions in inv.items():
                    for pos in positions:
                        word_pos.append((pos, word))
                word_pos.sort()
                abstract = " ".join(w for _, w in word_pos)

            author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "") if authors else "Unknown Authors"

            papers.append(
                {
                    "title": title.strip(),
                    "url": landing_url or pdf_url or "https://openalex.org",
                    "pdf_url": pdf_url,
                    "authors": authors,
                    "author": author_str,
                    "author_str": author_str,
                    "year": year,
                    "publisher": venue,
                    "venue": venue,
                    "abstract": abstract,
                    "snippet": abstract[:350] if abstract else title,
                    "is_paper": True,
                }
            )
        return papers[:max_results]
    except Exception:
        return []


def web_search(
    query: str,
    max_results: int = 5,
    timeout: int = 10,
    include_papers: bool = False,
) -> list[dict[str, Any]]:
    """Search the web via DuckDuckGo, with optional academic paper supplement.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
        timeout: Network timeout in seconds.
        include_papers: If True, merges academic paper results from OpenAlex.

    Returns:
        A list of ``{"title", "url", "snippet"}`` dicts (possibly empty).
    """
    if not query.strip():
        return []

    results: list[dict[str, Any]] = []

    if include_papers:
        papers = search_academic_papers(query, max_results=max_results, timeout=min(timeout, 6))
        for p in papers:
            results.append(
                {
                    "title": p["title"],
                    "url": p["url"],
                    "snippet": p["snippet"],
                    "abstract": p.get("abstract", ""),
                    "authors": p.get("authors", []),
                    "author": p.get("author", ""),
                    "year": p.get("year"),
                    "venue": p.get("venue", ""),
                    "pdf_url": p.get("pdf_url", ""),
                    "is_paper": True,
                }
            )

    if DDGS is not None and len(results) < max_results:
        try:
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
        except Exception:
            pass

    return results[:max_results]
