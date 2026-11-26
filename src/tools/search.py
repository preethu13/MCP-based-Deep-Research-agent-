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
    "mitigation", "contribute", "contributes", "impact", "impacts", "role", "roles",
    "vs", "versus", "difference", "differences", "compare", "comparison", "between"
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

    # Always anchor the search query with the main query topic/phrase to prevent topic drift
    anchor = ""
    if main_info and main_info["words"]:
        # If main query has 1 to 4 core terms, anchor with ALL of them so comparisons (e.g. "API vs MCP") don't drop half the query
        if len(main_info["words"]) <= 4:
            anchor = " ".join(main_info["words"])
        elif main_info["phrases"]:
            anchor = f'"{main_info["phrases"][0]}"'
        else:
            anchor = " ".join(main_info["words"][:3])
    elif main_info and main_info["phrases"]:
        anchor = f'"{main_info["phrases"][0]}"'

    if anchor:
        anchor_words = set(re.findall(r"\w+", anchor.lower()))
        distinguishing_words = [
            w for w in sub_info["words"]
            if w.lower() not in anchor_words and w.lower() not in _STOPWORDS
        ]
        aspects = " ".join(distinguishing_words[:2])
        return f'{anchor} {aspects}'.strip() if aspects else anchor

    # Fallback if no main_query was provided:
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
