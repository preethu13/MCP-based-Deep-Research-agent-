"""``web_search`` and ``search_academic_papers`` tools (MCP-01).

Query-to-URL retrieval via DuckDuckGo and OpenAlex Academic Index.
No API keys required. Free, open, and fast.
The tools never raise: on any failure they return an empty list and degrade gracefully.
"""

from __future__ import annotations

import json
import re
import threading
import urllib.parse
import urllib.request
from typing import Any

import httpx

from src.agent.profiler import get_profiler
from src.memory.cache import ResearchCache, normalize_cache_key

# The package was renamed duckduckgo_search -> ddgs; try the new name first.
try:  # pragma: no cover - import shim
    from ddgs import DDGS
except ImportError:  # pragma: no cover
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None  # type: ignore[assignment]


RELEVANCE_THRESHOLD = 6.0

_STOPWORDS = {
    "what", "how", "why", "when", "where", "which", "who", "whom", "whose",
    "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had", "having",
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "by", "about",
    "of", "from", "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "again", "further", "then", "once", "here", "there", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "can", "will", "just", "should", "now",
    "potential", "primary", "current", "real-world", "real", "world", "key",
    "causes", "mechanisms", "consequences", "strategies", "methods", "approaches", "mitigate",
    "mitigation", "contribute", "contributes", "impact", "impacts", "role", "roles"
}


def extract_query_concepts(query: str) -> dict[str, Any]:
    """Extracts core phrases, keywords, and acronyms from a query."""
    clean_q = query.lower().strip()
    norm_text = re.sub(r"[^a-zA-Z0-9\s-]", " ", clean_q)
    words = [w for w in norm_text.split() if w and w not in _STOPWORDS]

    # Generate bigrams and trigrams
    phrases = []
    tokens = norm_text.split()
    for i in range(len(tokens) - 1):
        w1, w2 = tokens[i], tokens[i + 1]
        if w1 not in _STOPWORDS and w2 not in _STOPWORDS:
            phrases.append(f"{w1} {w2}")
        elif i + 2 < len(tokens):
            w3 = tokens[i + 2]
            if w1 not in _STOPWORDS and w3 not in _STOPWORDS:
                phrases.append(f"{w1} {w2} {w3}")

    acronyms = [a.lower() for a in re.findall(r"\b[A-Z]{2,}\b", query)]

    return {
        "raw": query,
        "clean": clean_q,
        "words": words,
        "phrases": phrases,
        "acronyms": acronyms,
    }


def clean_search_query(sub_q: str, main_query: str = "") -> str:
    """Extracts concise, targeted search keywords from conversational sub-questions.

    Ensures the core topic phrase is kept intact and not diluted by noise words.
    """
    sub_info = extract_query_concepts(sub_q)
    main_info = extract_query_concepts(main_query) if main_query else None

    # Check if main_query has a specific multi-word phrase (e.g. "context rot")
    main_phrase = main_info["phrases"][0] if main_info and main_info["phrases"] else ""

    # If main_phrase exists and is NOT in sub_q, anchor sub_q with main_phrase
    if main_phrase and main_phrase not in sub_q.lower():
        sub_words = [w for w in sub_info["words"] if w not in _STOPWORDS]
        aspects = " ".join(sub_words[:2])
        return f'"{main_phrase}" {aspects}'.strip()

    # Otherwise, clean sub_q directly:
    if sub_info["phrases"]:
        core_phrase = sub_info["phrases"][0]
        other_words = [w for w in sub_info["words"] if w not in core_phrase.split() and w not in _STOPWORDS]
        aspects = " ".join(other_words[:2])
        return f'"{core_phrase}" {aspects}'.strip()
    elif sub_info["words"]:
        return " ".join(sub_info["words"][:4])

    return sub_q.strip()


def refine_search_queries(main_query: str, sub_q: str = "") -> list[str]:
    """Generates fallback refinement queries when initial retrieval yields 0 relevant papers."""
    main_info = extract_query_concepts(main_query)
    clean_main = " ".join(main_info["words"])
    refinements = []

    # 1. Exact quoted core phrase
    if main_info["phrases"]:
        refinements.append(f'"{main_info["phrases"][0]}"')

    # 2. Quoted phrase + "llm" or "artificial intelligence" if tech topic
    if main_info["phrases"] and "llm" not in main_info["words"]:
        refinements.append(f'"{main_info["phrases"][0]}" llm')

    # 3. Cleaned main query terms
    if clean_main and clean_main not in refinements:
        refinements.append(clean_main)

    # 4. Raw main query stripped of punctuation
    raw_clean = re.sub(r'[^\w\s-]', '', main_query).strip()
    if raw_clean and raw_clean not in refinements:
        refinements.append(raw_clean)

    return [r for r in refinements if r.strip()]


def score_paper_relevance(paper: dict[str, Any], root_query: str) -> float:
    """Scores paper relevance against the user's research topic.

    Considers phrase matching, core concept coverage, and handles acronym collisions
    and domain mismatches. Higher is better. A score < RELEVANCE_THRESHOLD (6.0)
    indicates an irrelevant or off-topic paper.
    """
    title = (paper.get("title") or "").strip()
    abstract = (
        paper.get("abstract")
        or paper.get("snippet")
        or paper.get("text")
        or ""
    ).strip()
    if not title:
        return 0.0

    title_lower = title.lower()
    abstract_lower = abstract.lower()
    combined_text = f"{title_lower} {abstract_lower}"

    q_info = extract_query_concepts(root_query)
    q_words = q_info["words"]
    q_phrases = q_info["phrases"]
    raw_query_lower = q_info["clean"]

    if not q_words and not q_phrases:
        return 1.0

    score = 0.0

    # 1. Exact raw query match in title (massive indicator) or abstract
    if raw_query_lower in title_lower:
        score += 25.0
    elif raw_query_lower in abstract_lower:
        score += 12.0
    elif len(q_words) == 1 and q_words[0] in title_lower:
        # Single-word topic exact match in title (e.g. "Redis", "Kubernetes")
        score += 20.0
    elif len(q_words) == 1 and q_words[0] in abstract_lower:
        # Single-word topic match in abstract (e.g. "Redis is an in-memory...")
        score += 8.0
        if len(re.findall(r"\b" + re.escape(q_words[0]) + r"\b", abstract_lower)) >= 2:
            score += 3.0

    # 2. Key phrase matching (e.g. "context rot", "attention mechanism")
    for phrase in q_phrases:
        if phrase in title_lower:
            score += 15.0
        elif phrase in abstract_lower:
            score += 7.0

    # 3. Individual word coverage
    matched_words = [w for w in q_words if re.search(r"\b" + re.escape(w) + r"\b", combined_text)]
    coverage_ratio = len(matched_words) / max(len(q_words), 1)

    if len(q_words) > 1:
        if coverage_ratio == 1.0:
            score += 6.0
        elif coverage_ratio >= 0.75:
            score += 3.0

    for w in q_words:
        if re.search(r"\b" + re.escape(w) + r"\b", title_lower):
            score += 4.0
        elif re.search(r"\b" + re.escape(w) + r"\b", abstract_lower):
            score += 2.0

    # 4. Strict concept requirements and false-friend / acronym disambiguation
    # A) "Context Rot"
    if "context" in q_words and "rot" in q_words:
        has_context_rot_phrase = "context rot" in combined_text or "context-rot" in combined_text
        has_context_degradation = "context" in combined_text and any(
            term in combined_text
            for term in [
                "degradation", "degrades", "decay", "attention loss", "coherence failure",
                "long-context", "long context", "effective context", "context length"
            ]
        )
        has_rot = bool(re.search(r"\brot\b|\brots\b", combined_text))

        if not (has_context_rot_phrase or (has_rot and has_context_degradation)):
            return -25.0

        # Disambiguate "RoT: Reflection on Trees", "Concept-ROT", "Root of Trust"
        if re.search(r"\b(reflection on (search )?trees|model editing|poisoning concepts|root of trust)\b", combined_text):
            if not has_context_rot_phrase:
                return -30.0

        # Disambiguate social media "brain rot"
        if "brain rot" in combined_text and not has_context_rot_phrase:
            return -30.0

    # B) "Retrieval-Augmented Generation" / "RAG"
    if any(term in q_words for term in ["rag", "retrieval-augmented", "retrieval augmented"]):
        bio_terms = ["gene", "recombination", "antigen", "lymphocyte", "rag1", "rag2", "dna cleavage", "immune system", "v(d)j"]
        if any(b in combined_text for b in bio_terms):
            if not any(ai_term in combined_text for ai_term in ["language model", "llm", "nlp", "generation", "document retrieval"]):
                return -35.0
        if "red-amber-green" in combined_text or "red amber green" in combined_text:
            return -35.0

    # C) "Transformer Attention Mechanism"
    if "attention" in q_words and ("transformer" in q_words or "transformers" in q_words or "mechanism" in q_words):
        psych_terms = ["adhd", "schizophrenia", "children", "psychological", "deficit hyperactivity", "pediatric"]
        if any(m in combined_text for m in psych_terms):
            if not any(dl in combined_text for dl in ["neural network", "transformer", "bert", "gpt", "deep learning"]):
                return -35.0

    # D) "Hallucination in Large Language Models"
    if "hallucination" in q_words and any(w in q_words for w in ["llm", "llms", "language", "models"]):
        clinical_psych = ["psychosis", "schizophrenia", "bipolar", "visual hallucination", "auditory hallucination", "antipsychotic"]
        if any(p in combined_text for p in clinical_psych):
            if not any(nlp in combined_text for nlp in ["language model", "llm", "text generation", "gpt", "nlp"]):
                return -35.0

    # E) "Vector Database Retrieval"
    if "vector" in q_words and ("database" in q_words or "retrieval" in q_words):
        bio_vectors = ["mosquito", "malaria", "dengue", "aedes", "parasite", "viral vector", "plasmid", "insecticide"]
        if any(bv in combined_text for bv in bio_vectors):
            if not any(db in combined_text for db in ["database", "embedding", "nearest neighbor", "faiss", "milvus", "ann", "similarity search"]):
                return -35.0

    # 5. General domain penalty for completely unrelated finance/real estate
    finance_terms = ["investing", "stock market", "portfolio management", "real estate", "equity trading"]
    if not any(f in raw_query_lower for f in finance_terms):
        if any(f in title_lower for f in finance_terms):
            score -= 20.0

    # 6. Coverage penalty: if less than half of significant query concepts match
    if len(q_words) >= 2 and coverage_ratio < 0.5:
        score -= 12.0

    return score


def is_paper_relevant(paper: dict[str, Any], root_query: str, threshold: float = RELEVANCE_THRESHOLD) -> bool:
    """Returns True if the paper scores at or above the relevance threshold."""
    return score_paper_relevance(paper, root_query) >= threshold


def is_candidate_relevant(
    paper: dict[str, Any], root_query: str, sub_q: str = "", threshold: float = RELEVANCE_THRESHOLD
) -> bool:
    """Check relevance against root query and optional sub-question with hard false-friend exclusion."""
    main_score = score_paper_relevance(paper, root_query)
    if main_score < -10.0:
        return False
    if sub_q:
        sub_score = score_paper_relevance(paper, sub_q)
        if sub_score < -10.0:
            return False
        return max(main_score, sub_score) >= threshold
    return main_score >= threshold


def classify_publication_status(
    item_or_paper: dict[str, Any],
    landing_url: str = "",
    venue: str = "",
    doi: str = "",
) -> tuple[str, bool]:
    """Classifies paper publication status and verifies peer-reviewed status.

    Returns:
        (status_label, is_peer_reviewed)
        where status_label is one of:
          - "Preprint (arXiv)"
          - "Preprint"
          - "Peer-reviewed journal article"
          - "Peer-reviewed conference paper"
          - "Other publication"
          - "Unknown publication status"
    """
    type_str = str(item_or_paper.get("type", "")).lower()
    source_type = ""
    source_name = ""
    primary_loc = item_or_paper.get("primary_location")
    if isinstance(primary_loc, dict):
        source = primary_loc.get("source") or {}
        if isinstance(source, dict):
            source_type = str(source.get("type", "")).lower()
            source_name = str(source.get("display_name", "")).lower()

    url_lower = (landing_url or item_or_paper.get("url") or "").lower()
    doi_lower = (doi or item_or_paper.get("doi") or "").lower()
    venue_lower = (venue or item_or_paper.get("venue") or item_or_paper.get("publisher") or "").lower()

    # 1. arXiv detection — NEVER classify arXiv as peer-reviewed
    is_arxiv = (
        "arxiv" in url_lower
        or "arxiv" in doi_lower
        or "arxiv" in venue_lower
        or "arxiv" in source_name
    )
    if is_arxiv:
        return "Preprint (arXiv)", False

    # 2. Other Preprint repositories
    other_repos = ["biorxiv", "medrxiv", "ssrn", "research square", "chemrxiv", "preprints.org"]
    is_other_preprint = (
        type_str == "preprint"
        or source_type == "repository"
        or any(r in url_lower or r in venue_lower for r in other_repos)
    )
    if is_other_preprint:
        return "Preprint", False

    # 3. Peer-reviewed journal articles (check first if explicitly typed as journal)
    is_journal = (
        type_str in ("journal-article", "article")
        or source_type == "journal"
        or ("journal" in venue_lower or "transactions" in venue_lower or "nature" in venue_lower or "science" in venue_lower)
    )
    if is_journal and venue_lower and not any(r in venue_lower for r in ["arxiv", "preprint", "repository"]):
        return "Peer-reviewed journal article", True

    # 4. Peer-reviewed conference papers
    conf_keywords = [
        "conference", "proceedings", "symposium", "workshop",
        "neurips", "icml", "acl", "emnlp", "naacl", "iclr", "cvpr", "iccv",
        "eccv", "kdd", "aaai", "ijcai", "sigir", "sigmod", "vldb"
    ]
    is_conf = (
        type_str in ("proceedings-article", "conference", "proceedings")
        or source_type == "conference"
        or any(k in venue_lower for k in conf_keywords)
    )
    if is_conf:
        return "Peer-reviewed conference paper", True

    if venue_lower and venue_lower not in ("venue unavailable", "unknown", "n/a"):
        return "Other publication", False

    return "Unknown publication status", False


def classify_evidence_tier(paper: dict[str, Any], root_query: str, sub_q: str = "") -> str:
    """Classifies paper into Direct evidence, Supporting evidence, or Related work.

    Does NOT classify purely by title keyword match. Uses abstract content,
    methodology indicators, and concept depth.
    """
    title = (paper.get("title") or "").lower()
    abstract = (paper.get("abstract") or paper.get("snippet") or paper.get("text") or "").lower()
    combined = f"{title} {abstract}"

    # Methodological indicators
    empirical_indicators = [
        "diagnos", "measur", "evaluat", "benchmark", "empiric", "experiment",
        "we find", "our experiments show", "performance degrades", "degradation",
        "abandon", "failure", "investigat", "study of", "attention predict"
    ]
    proposed_indicators = [
        "we propose", "propose a", "protocol", "architecture", "framework",
        "calculus", "state-coupling", "coherence protocol", "approach to solve",
        "paradigm", "blueprint"
    ]

    has_empirical = any(re.search(r"\b" + re.escape(w), combined) for w in empirical_indicators)
    has_proposed = any(re.search(r"\b" + re.escape(w), combined) for w in proposed_indicators)

    # Core query concepts match
    q_info = extract_query_concepts(root_query)
    q_words = q_info["words"]
    has_all_core = all(re.search(r"\b" + re.escape(w) + r"\b", combined) for w in q_words)

    # Context rot specific nuances
    if "context" in q_words and "rot" in q_words:
        if "long-horizon search" in combined or "degrades with context length" in combined or "attention predicts" in combined:
            return "Direct evidence"
        if "classifier" in combined or "monitor performance" in combined:
            return "Direct evidence" if has_empirical else "Supporting evidence"
        if has_proposed or "protocol" in combined or "architecture" in combined or "mcp" in combined:
            return "Related work"

    # General domain rules
    if has_all_core and has_empirical and not (has_proposed and not has_empirical):
        return "Direct evidence"
    elif has_all_core or has_empirical:
        return "Supporting evidence"
    else:
        return "Related work"


def is_simulation_study(paper: dict[str, Any]) -> bool:
    """Detects if findings are derived from synthetic simulation vs real-world deployment."""
    combined = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    sim_terms = [
        "simulation", "simulated", "synthetic", "controlled environment",
        "synthetic benchmark", "toy environment", "in silico"
    ]
    return any(re.search(r"\b" + re.escape(s) + r"\b", combined) for s in sim_terms)


_HTTPX_CLIENT: httpx.Client | None = None
_CLIENT_LOCK = threading.Lock()


def _get_http_client(timeout: int = 8) -> httpx.Client:
    global _HTTPX_CLIENT
    with _CLIENT_LOCK:
        if _HTTPX_CLIENT is None or _HTTPX_CLIENT.is_closed:
            _HTTPX_CLIENT = httpx.Client(
                timeout=httpx.Timeout(timeout, connect=4.0),
                limits=httpx.Limits(max_keepalive_connections=15, max_connections=30),
                headers={
                    "User-Agent": "DeepResearchAgent/1.0 (mailto:researcher@local.ai)",
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )
        return _HTTPX_CLIENT


def search_academic_papers(
    query: str,
    max_results: int = 5,
    timeout: int = 8,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """Search for academic papers and scientific preprints via OpenAlex.

    Returns structured dictionaries containing:
        - title: Paper title
        - url: Direct paper / DOI landing URL
        - pdf_url: Open access direct PDF URL (if available)
        - doi: Valid DOI URL
        - authors: List of author names
        - author: Formatted author string
        - author_str: Formatted author string
        - year: Publication year
        - venue: Journal, conference or repository venue
        - publication_status: "Preprint (arXiv)", "Peer-reviewed journal article", etc.
        - is_peer_reviewed: bool
        - evidence_tier: "Direct evidence", "Supporting evidence", "Related work"
        - is_simulation: bool
        - abstract: Full paper abstract
        - snippet: Concise excerpt
        - is_paper: True
    """
    clean_q = query.strip()
    if not clean_q:
        return []

    cache = ResearchCache.get_instance() if use_cache else None
    cache_key = f"{normalize_cache_key(clean_q)}_{max_results}"
    if cache is not None:
        cached = cache.get("academic_search", cache_key)
        if cached is not None and isinstance(cached, list):
            return cached

    prof = get_profiler()
    with prof.measure_operation("openalex"):
        try:
            encoded = urllib.parse.quote_plus(clean_q)
            url = f"https://api.openalex.org/works?search={encoded}&per-page={max(1, max_results)}"
            client = _get_http_client(timeout=timeout)
            resp = client.get(url, timeout=timeout)
            if resp.status_code != 200:
                return []
            data = resp.json()

            papers: list[dict[str, Any]] = []
            for item in data.get("results", []):
                title = item.get("title")
                if not title:
                    continue

                doi = item.get("doi") or ""
                if doi and not doi.startswith("http"):
                    doi_url = f"https://doi.org/{doi.lstrip('/')}"
                else:
                    doi_url = doi

                primary_loc = item.get("primary_location") or {}
                source_obj = primary_loc.get("source") or {}
                venue = source_obj.get("display_name") or ""
                source_type = source_obj.get("type") or ""

                landing_url = (
                    primary_loc.get("landing_page_url")
                    or doi_url
                    or (item.get("open_access") or {}).get("oa_url")
                    or ""
                )
                pdf_url = (primary_loc.get("pdf_url") or "") or ((item.get("open_access") or {}).get("oa_url") or "")

                authors = [
                    a.get("author", {}).get("display_name", "").strip()
                    for a in item.get("authorships", [])
                    if a.get("author", {}).get("display_name")
                ]
                year = item.get("publication_year")

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

                pub_status, is_peer_reviewed = classify_publication_status(
                    item, landing_url=landing_url, venue=venue, doi=doi_url
                )

                # Display string for author
                if not authors:
                    author_str = "Authors unavailable"
                elif len(authors) == 1:
                    author_str = authors[0]
                elif len(authors) == 2:
                    author_str = f"{authors[0]} & {authors[1]}"
                else:
                    author_str = f"{authors[0]} et al."

                clean_url = landing_url or pdf_url or doi_url or "https://openalex.org"

                paper_dict = {
                    "title": title.strip(),
                    "abstract": abstract,
                    "url": clean_url,
                    "venue": venue or ("arXiv" if "arXiv" in pub_status else "Venue unavailable"),
                }
                evidence_tier = classify_evidence_tier(paper_dict, clean_q)
                is_sim = is_simulation_study(paper_dict)

                papers.append(
                    {
                        "title": title.strip(),
                        "url": clean_url,
                        "pdf_url": pdf_url,
                        "doi": doi_url,
                        "authors": authors,
                        "author": author_str,
                        "author_str": author_str,
                        "year": year,
                        "publisher": venue or ("arXiv" if "arXiv" in pub_status else ""),
                        "venue": venue or ("arXiv" if "arXiv" in pub_status else "Venue unavailable"),
                        "source_type": source_type,
                        "publication_status": pub_status,
                        "is_peer_reviewed": is_peer_reviewed,
                        "evidence_tier": evidence_tier,
                        "is_simulation": is_sim,
                        "abstract": abstract,
                        "snippet": abstract[:350] if abstract else title,
                        "is_paper": True,
                    }
                )

            final_papers = papers[:max_results]
            if cache is not None and final_papers:
                cache.set("academic_search", cache_key, final_papers)
            return final_papers
        except Exception:
            return []


def web_search(
    query: str,
    max_results: int = 5,
    timeout: int = 10,
    include_papers: bool = False,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """Search the web via DuckDuckGo, with optional academic paper supplement.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
        timeout: Network timeout in seconds.
        include_papers: If True, merges academic paper results from OpenAlex.
        use_cache: Whether to use caching.

    Returns:
        A list of ``{"title", "url", "snippet"}`` dicts (possibly empty).
    """
    if not query.strip():
        return []

    # Detect test mock DDGS: bypass cache if DDGS is monkeypatched
    is_mock = DDGS is not None and getattr(DDGS, "__module__", "") not in ("ddgs", "duckduckgo_search")
    cache = ResearchCache.get_instance() if (use_cache and not is_mock) else None
    cache_key = f"{normalize_cache_key(query)}_{max_results}_{include_papers}"
    if cache is not None:
        cached = cache.get("web_search", cache_key)
        if cached is not None and isinstance(cached, list):
            return cached

    results: list[dict[str, Any]] = []

    if include_papers:
        papers = search_academic_papers(query, max_results=max_results, timeout=min(timeout, 6), use_cache=use_cache)
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

    prof = get_profiler()
    with prof.measure_operation("ddg"):
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

    final_results = results[:max_results]
    if cache is not None and final_results:
        cache.set("web_search", cache_key, final_results)
    return final_results
