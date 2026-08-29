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

        # 3. web search
        results = deps.tools.web_search(sub_q, settings.max_results_per_query)
        trace.append(
            make_event(
                len(trace) + 1,
                "researcher",
                "web_search",
                f"Searched the web · {sub_q[:60]}",
                f"{len(results)} result(s)",
                "ok" if results else "warn",
            )
        )
        if not results:
            warnings.append(f"No search results for: {sub_q}")
            research.append(item)
            continue

        # 4. scrape top sources in parallel with graceful degradation
        targets = results[: settings.sources_to_scrape]
        from concurrent.futures import ThreadPoolExecutor

        def _fetch_one(res: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
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
                    "title": scraped.get("title") or result["title"],
                    "text": combined_text,
                    "method": method,
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
