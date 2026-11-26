"""Researcher node (AG-02, AG-03, AG-05, AG-07).

For each sub-question:

1. Recall relevant prior findings from memory *first* (recall-before-search).
2. If enough strong memory hits exist, short-circuit and skip the web entirely.
3. Otherwise search the web, then scrape the top sources.
4. Degrade gracefully — a failed source falls back to its search snippet and is
   logged as a warning, never crashing the run.
"""

from __future__ import annotations

from typing import Any

from src.agent.state import AgentDeps, ResearchState, make_event
from src.tools.search import (
    RELEVANCE_THRESHOLD,
    clean_search_query,
    is_candidate_relevant,
    is_paper_relevant,
    refine_search_queries,
    score_paper_relevance,
)

_MIN_SCRAPE_WORDS = 5   # keep even short snippets — something beats nothing
_MAX_CONTEXT_CHARS = 6000


def researcher_node(state: ResearchState, deps: AgentDeps) -> dict[str, Any]:
    settings = deps.settings
    session_id = state["session_id"]
    main_query = state.get("query", "")
    research: list[dict[str, Any]] = []
    trace = list(state.get("trace", []))
    warnings = list(state.get("warnings", []))

    for sub_q in state.get("sub_questions", []):
        item: dict[str, Any] = {
            "sub_question": sub_q,
            "sources": [],
            "memory_hits": [],
            "used_memory": False,
        }

        def _score(c: dict[str, Any]) -> float:
            m_s = score_paper_relevance(c, main_query)
            if m_s < -10.0:
                return m_s
            s_s = score_paper_relevance(c, sub_q)
            if s_s < -10.0:
                return s_s
            return max(m_s, s_s)

        # 1. Recall memory as supplementary context only (never replaces fresh search)
        raw_hits = deps.tools.recall_memory("all", sub_q, top_k=5)
        # Validate memory relevance against the research topic before using
        validated_hits = [
            h for h in raw_hits
            if _score({"title": h.get("content", "")[:120], "abstract": h.get("content", "")}) >= RELEVANCE_THRESHOLD
        ]
        item["memory_hits"] = validated_hits
        trace.append(
            make_event(
                len(trace) + 1,
                "researcher",
                "recall_memory",
                f"Checked memory (supplementary) · {sub_q[:60]}",
                f"{len(validated_hits)} validated recollection(s) ({len(raw_hits)} raw)",
                "ok",
            )
        )

        # 2. Fresh Search & Retrieval (Primary evidence by default)
        search_q = clean_search_query(sub_q, main_query)
        academic_fn = getattr(deps.tools, "search_academic_papers", None)

        def _retrieve(q_str: str) -> list[dict[str, Any]]:
            papers = []
            if callable(academic_fn):
                papers = academic_fn(q_str, max_results=settings.max_results_per_query)
            webs = deps.tools.web_search(q_str, settings.max_results_per_query)
            seen_u = set()
            merged = []
            for r in papers + webs:
                u = r.get("url", "")
                if u and u not in seen_u:
                    seen_u.add(u)
                    merged.append(r)
            return merged

        candidates = _retrieve(search_q)

        # Score and filter candidates against main_query and sub_q
        scored = [(_score(c), c) for c in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [c for s, c in scored if s >= RELEVANCE_THRESHOLD]

        # 3. Query Refinement if 0 candidates pass the relevance threshold
        if not results:
            refinements = refine_search_queries(main_query, sub_q)
            for ref_q in refinements:
                if ref_q == search_q:
                    continue
                ref_candidates = _retrieve(ref_q)
                ref_scored = [(_score(c), c) for c in ref_candidates]
                ref_scored.sort(key=lambda x: x[0], reverse=True)
                passing = [c for s, c in ref_scored if s >= RELEVANCE_THRESHOLD]
                if passing:
                    results = passing
                    trace.append(
                        make_event(
                            len(trace) + 1,
                            "researcher",
                            "query_refinement",
                            f"Refined search query · {ref_q[:60]}",
                            f"Found {len(results)} relevant source(s)",
                            "ok",
                        )
                    )
                    break

        trace.append(
            make_event(
                len(trace) + 1,
                "researcher",
                "web_search",
                f"Retrieved academic sources · {search_q[:60]}",
                f"{len(results)} verified relevant source(s) ({len([r for r in results if r.get('is_paper')])} paper(s))",
                "ok" if results else "warn",
            )
        )

        # STRICT: Never include an irrelevant paper just to avoid returning zero results!
        if not results:
            warnings.append(f"No relevant academic papers or web sources met the relevance threshold for: {sub_q}")
            research.append(item)
            continue

        # 4. Gather source text (fast-path: papers with abstracts skip network scraping)
        targets = results[: settings.sources_to_scrape]
        from concurrent.futures import ThreadPoolExecutor

        def _fetch_one(res: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
            if res.get("abstract"):
                # Paper with authentic abstract already in hand — instant retrieval
                return res, {
                    "url": res["url"],
                    "title": res.get("title", ""),
                    "text": res["abstract"],
                    "word_count": len(res["abstract"].split()),
                    "method_used": "academic_index",
                }
            try:
                scraped = deps.tools.scrape_page(res["url"])
            except Exception as exc:
                scraped = {"url": res["url"], "error": str(exc), "word_count": 0, "method_used": "failed"}
            return res, scraped

        with ThreadPoolExecutor(max_workers=min(len(targets), 5)) as executor:
            scraped_pairs = list(executor.map(_fetch_one, targets))

        for result, scraped in scraped_pairs:
            snippet_text = (result.get("snippet") or "").strip()
            page_text = (scraped.get("text") or "").strip() if not scraped.get("error") else ""

            # Hybrid text: combine search snippet + scraped page text for maximum context quality
            if snippet_text and page_text and snippet_text not in page_text:
                combined_text = f"Summary Snippet: {snippet_text}\n\nPage Text: {page_text[:_MAX_CONTEXT_CHARS]}"
            elif page_text:
                combined_text = page_text[:_MAX_CONTEXT_CHARS]
            elif snippet_text:
                combined_text = snippet_text
            else:
                combined_text = result["title"]

            method = scraped.get("method_used", "static")
            if scraped.get("error") or len(page_text.split()) < _MIN_SCRAPE_WORDS:
                method = "snippet" if snippet_text else "failed"
                warnings.append(
                    f"Used search snippet for {result['url']}: "
                    f"{scraped.get('error', 'thin page content')}"
                )

            item["sources"].append(
                {
                    "url": result["url"],
                    "title": scraped.get("title") or result.get("title"),
                    "text": combined_text,
                    "method": method,
                    "author": result.get("author") or result.get("author_str", ""),
                    "authors": result.get("authors", []),
                    "year": result.get("year"),
                    "venue": result.get("venue") or result.get("publisher", ""),
                    "pdf_url": result.get("pdf_url", ""),
                    "abstract": result.get("abstract", ""),
                    "is_paper": result.get("is_paper", False),
                }
            )
            trace.append(
                make_event(
                    len(trace) + 1,
                    "researcher",
                    "scrape_page",
                    f"Gathered source ({method})",
                    f"{len(combined_text.split())} words · {result['url']}",
                    "ok" if method != "failed" else "warn",
                )
            )

        research.append(item)

    return {"research": research, "trace": trace, "warnings": warnings}
