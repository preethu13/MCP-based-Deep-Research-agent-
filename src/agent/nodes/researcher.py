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
from src.tools.search import clean_search_query, score_paper_relevance

_MIN_SCRAPE_WORDS = 5   # keep even short snippets — something beats nothing
_MAX_CONTEXT_CHARS = 6000


def researcher_node(state: ResearchState, deps: AgentDeps) -> dict[str, Any]:
    settings = deps.settings
    session_id = state["session_id"]
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

        # 1. recall-before-search (cross-session recall via 'all')
        hits = deps.tools.recall_memory("all", sub_q, top_k=5)
        item["memory_hits"] = hits
        trace.append(
            make_event(
                len(trace) + 1,
                "researcher",
                "recall_memory",
                f"Checked memory · {sub_q[:60]}",
                f"{len(hits)} relevant recollection(s)",
                "ok",
            )
        )

        # 2. short-circuit if memory already answers it
        if len(hits) >= settings.recall_shortcircuit_hits:
            item["used_memory"] = True
            trace.append(
                make_event(
                    len(trace) + 1,
                    "researcher",
                    "recall_memory",
                    "Answered from memory — skipped web search",
                    sub_q[:80],
                    "ok",
                )
            )
            research.append(item)
            continue

        main_query = state.get("query", "")
        search_q = clean_search_query(sub_q, main_query)

        # 3. Academic paper and web search with focused keywords
        academic_fn = getattr(deps.tools, "search_academic_papers", None)
        paper_results: list[dict[str, Any]] = []
        if callable(academic_fn):
            paper_results = academic_fn(search_q, max_results=settings.max_results_per_query)
            # Supplement with root topic if few papers returned
            if len(paper_results) < 2 and main_query and main_query != search_q:
                extra = academic_fn(main_query, max_results=settings.max_results_per_query)
                seen_titles = {p.get("title") for p in paper_results}
                for ep in extra:
                    if ep.get("title") not in seen_titles:
                        paper_results.append(ep)

        web_results = deps.tools.web_search(search_q, settings.max_results_per_query)

        # Merge, prioritizing academic papers with verified abstracts
        seen_urls = set()
        candidates: list[dict[str, Any]] = []
        for r in paper_results + web_results:
            u = r.get("url", "")
            if u and u not in seen_urls:
                seen_urls.add(u)
                candidates.append(r)

        # Relevance scoring & re-ranking against main research topic
        scored = [(score_paper_relevance(c, main_query), c) for c in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)

        # Retain relevant candidates (positive relevance score)
        results = [c for s, c in scored if s >= 0.5]
        if not results and scored:
            # Fall back to best candidate if filter was too strict
            results = [scored[0][1]]

        trace.append(
            make_event(
                len(trace) + 1,
                "researcher",
                "web_search",
                f"Retrieved academic sources · {search_q[:60]}",
                f"{len(results)} relevant source(s) ({len([r for r in results if r.get('is_paper')])} paper(s))",
                "ok" if results else "warn",
            )
        )
        if not results:
            warnings.append(f"No search results for: {sub_q}")
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
