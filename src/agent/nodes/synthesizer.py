"""Synthesizer node (AG-04, AG-06, FC-01, hallucination mitigation).

Drafts a grounded claim per sub-question strictly from the scraped/recalled
context, attaches a citation to every source used, persists findings + citations
to SQLite, and stores each finding back into semantic memory for future recall.

For ``comparison`` output it additionally attempts to pivot the notes into an
entities x dimensions table (best-effort; falls back to the question/finding
table in the formatter if the model can't produce clean JSON).
"""

from __future__ import annotations

from typing import Any

from src.agent.state import AgentDeps, ResearchState, make_event
from src.tools.search import RELEVANCE_THRESHOLD, is_candidate_relevant, score_paper_relevance

_SYNTH_SYSTEM = (
    "You are a strict, evidence-grounded scientific research analyst. Write a concise, 2-3 sentence "
    "finding that answers the sub-question based STRICTLY on the provided sources and abstracts.\n"
    "CRITICAL RULES:\n"
    "1. Base all facts, definitions, mechanisms, and conclusions SOLELY on the provided source text. "
    "Do NOT fill in gaps or hallucinate using external training knowledge.\n"
    "2. If the sources do not provide clear, credible evidence answering the question, state: "
    "'Insufficient direct evidence in the retrieved sources to address this question.'\n"
    "3. Define concepts accurately using ONLY the definitions stated in the papers.\n"
    "4. Do NOT output citation numbers like [1] or bracketed references; they are attached automatically."
)

_COMPARE_SYSTEM = (
    "You convert research notes into a structured comparison. Return ONLY JSON of "
    'the form {"dimensions": ["..."], "entities": [{"name": "...", "attributes": '
    '{"dimension": "short value"}}]}. Compare every entity across the same '
    "dimensions. Keep values short (a few words)."
)


def _synthesize_claim(llm: Any, sub_q: str, context: str) -> str:
    user = f"Sub-question: {sub_q}\n\nSources:\n{context[:3000]}"
    try:
        claim = llm.complete(_SYNTH_SYSTEM, user, max_tokens=200).strip()
        return claim or f"Insufficient reliable evidence in retrieved sources to address: {sub_q}."
    except Exception:
        # LLM unreachable mid-run — degrade instead of crashing (FC-05/FC-07).
        snippet = context[:300].replace("\n", " ")
        return f"(Unverified) Based on the gathered sources: {snippet}…"


def _clean_claim_item(x: Any) -> str:
    if isinstance(x, dict):
        val = x.get("finding") or x.get("claim") or x.get("answer") or x.get("summary")
        if val:
            return str(val).strip()
        vals = list(x.values())
        return str(vals[-1]).strip() if vals else ""
    return str(x).strip()


def _batch_synthesize_claims(llm: Any, items: list[tuple[str, str]]) -> list[str]:
    """Synthesize findings for multiple sub-questions in a single fast LLM pass."""
    if not items:
        return []
    if len(items) == 1:
        return [_synthesize_claim(llm, items[0][0], items[0][1])]

    prompt_parts = []
    for idx, (sub_q, ctx) in enumerate(items, start=1):
        prompt_parts.append(f"Sub-question {idx}: {sub_q}\nSources:\n{ctx[:1800]}")
    user = "\n\n---\n\n".join(prompt_parts)

    system = (
        "You are a strict, evidence-grounded scientific research analyst. For each sub-question below, "
        "write a 2-3 sentence factual finding based EXCLUSIVELY on the provided source excerpts.\n"
        "RULES:\n"
        "- Rely ONLY on explicit statements in the excerpts. Do NOT extrapolate or assume.\n"
        "- If an excerpt does not contain credible evidence for a sub-question, explicitly output: "
        "\"Insufficient reliable evidence in retrieved sources to address this question.\"\n"
        "- Return ONLY a JSON array of strings corresponding to each sub-question in order."
    )
    try:
        data = llm.complete_json(system, user, max_tokens=300)
        if isinstance(data, list) and len(data) == len(items):
            results = [_clean_claim_item(x) for x in data]
            # Fallback any empty claims to individual synthesis
            for i, (claim, (sub_q, ctx)) in enumerate(zip(results, items)):
                if not claim.strip():
                    results[i] = _synthesize_claim(llm, sub_q, ctx)
            return results
        if isinstance(data, dict):
            claims = data.get("findings") or data.get("claims") or list(data.values())
            if isinstance(claims, list) and len(claims) == len(items):
                results = [_clean_claim_item(x) for x in claims]
                for i, (claim, (sub_q, ctx)) in enumerate(zip(results, items)):
                    if not claim.strip():
                        results[i] = _synthesize_claim(llm, sub_q, ctx)
                return results
    except Exception:
        pass

    return [_synthesize_claim(llm, sub_q, ctx) for sub_q, ctx in items]


def _persist(deps: AgentDeps, session_id: str, finding: dict[str, Any]) -> None:
    try:
        finding_id = deps.sqlite.add_finding(
            session_id, finding.get("sub_question"), finding["claim"], finding["confidence"]
        )
        for source in finding.get("sources", []):
            deps.sqlite.add_citation(
                finding_id,
                source["url"],
                source.get("title"),
                None,
                None,
                deps.tools.generate_citation(source, "apa"),
                deps.tools.generate_citation(source, "mla"),
            )
    except Exception:
        pass  # persistence is best-effort; never break the run


def _structure_comparison(
    deps: AgentDeps, state: ResearchState, findings: list[dict[str, Any]]
) -> list[dict[str, Any]] | None:
    notes = "\n\n".join(
        f"{f.get('sub_question')}: {f.get('claim')}" for f in findings if f.get("claim")
    )
    user = f"Question: {state['query']}\n\nResearch notes:\n{notes}"
    try:
        data = deps.llm.complete_json(_COMPARE_SYSTEM, user)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    all_citations: list[str] = []
    for finding in findings:
        for citation in finding.get("citations", []):
            if citation not in all_citations:
                all_citations.append(citation)

    entity_findings: list[dict[str, Any]] = []
    for entity in data.get("entities", []) or []:
        name = str(entity.get("name", "")).strip()
        attributes = entity.get("attributes")
        if not name or not isinstance(attributes, dict):
            continue
        entity_findings.append(
            {
                "sub_question": None,
                "entity": name,
                "claim": name,
                "attributes": {str(k): str(v) for k, v in attributes.items()},
                "citations": all_citations,
                "sources": [],
                "confidence": 0.8,
            }
        )
    return entity_findings if len(entity_findings) >= 2 else None


def synthesizer_node(state: ResearchState, deps: AgentDeps) -> dict[str, Any]:
    style = state.get("citation_style", "apa")
    fmt = state.get("output_format", "brief")
    main_query = state.get("query", "")
    findings: list[dict[str, Any]] = []
    trace = list(state.get("trace", []))

    valid_items = []
    for item in state.get("research", []):
        sub_q = item["sub_question"]
        raw_sources = item.get("sources", [])
        raw_memory = item.get("memory_hits", [])

        # Strict Relevance Verification: prune any source or memory that fails the threshold
        verified_sources = [
            s for s in raw_sources
            if is_candidate_relevant(s, main_query, sub_q)
        ]
        verified_memory = [
            m for m in raw_memory
            if is_candidate_relevant(
                {"title": m.get("content", "")[:120], "abstract": m.get("content", "")},
                main_query,
                sub_q,
            )
        ]

        if not verified_sources and not verified_memory:
            findings.append(
                {
                    "sub_question": sub_q,
                    "claim": f"No verified relevant research papers or sources were found for: {sub_q}.",
                    "citations": [],
                    "sources": [],
                    "papers": [],
                    "confidence": 0.0,
                }
            )
            trace.append(
                make_event(
                    len(trace) + 1, "synthesizer", "synthesize", "No verified sources", sub_q[:80], "warn"
                )
            )
        else:
            context_parts = [
                f"[{i}] {s.get('title', '')}\nURL: {s.get('url', '')}\n{s.get('text', '')}"
                for i, s in enumerate(verified_sources, start=1)
            ]
            context_parts += [f"[memory] {m.get('content', '')}" for m in verified_memory]
            valid_items.append((item, sub_q, verified_sources, "\n\n".join(context_parts)))

    # Batch synthesize all findings in a single fast LLM pass
    if valid_items:
        synthesized_claims = _batch_synthesize_claims(
            deps.llm, [(sub_q, ctx) for _, sub_q, _, ctx in valid_items]
        )

        for (item, sub_q, verified_sources, _), claim in zip(valid_items, synthesized_claims):
            is_insufficient = (
                "insufficient" in claim.lower()
                or "no direct evidence" in claim.lower()
                or "no verified" in claim.lower()
                or not verified_sources
            )

            citations = (
                [deps.tools.generate_citation(s, style) for s in verified_sources]
                if not is_insufficient
                else []
            )
            used_sources = (
                [
                    {
                        "url": s["url"],
                        "title": s["title"],
                        "author": s.get("author", ""),
                        "year": s.get("year"),
                        "publisher": s.get("venue") or s.get("publisher", ""),
                    }
                    for s in verified_sources
                ]
                if not is_insufficient
                else []
            )

            # Collect structured paper entries for academic literature presentation
            papers = []
            if not is_insufficient:
                for s in verified_sources:
                    is_academic = (
                        s.get("is_paper")
                        or bool(s.get("abstract"))
                        or "doi.org" in s.get("url", "")
                        or "arxiv.org" in s.get("url", "")
                        or "openalex.org" in s.get("url", "")
                    )
                    abstract_text = s.get("abstract") or s.get("text", "")
                    summary_clean = abstract_text.strip()
                    if len(summary_clean) > 800:
                        summary_clean = summary_clean[:800] + "…"

                    papers.append(
                        {
                            "title": s.get("title", ""),
                            "url": s.get("url", ""),
                            "pdf_url": s.get("pdf_url", ""),
                            "author": s.get("author", ""),
                            "authors": s.get("authors", []),
                            "year": s.get("year"),
                            "venue": s.get("venue", ""),
                            "summary": summary_clean,
                            "is_paper": is_academic,
                        }
                    )

            finding = {
                "sub_question": sub_q,
                "claim": claim,
                "citations": citations,
                "sources": used_sources,
                "papers": papers,
                "confidence": 0.9 if verified_sources and not is_insufficient else 0.1,
            }

            if verified_sources and not is_insufficient:
                _persist(deps, state["session_id"], finding)
                # Store finding for future cross-session recall only when backed by valid evidence
                deps.tools.store_memory(
                    state["session_id"], f"Q: {sub_q}\nA: {claim}", {"topic": sub_q[:120]}
                )

            trace.append(
                make_event(
                    len(trace) + 1,
                    "synthesizer",
                    "synthesize",
                    "Synthesized finding",
                    f"{len(citations)} citation(s) from {len(verified_sources)} source(s)",
                    "ok" if not is_insufficient else "warn",
                )
            )
            findings.append(finding)

    if fmt == "comparison":
        pivoted = _structure_comparison(deps, state, findings)
        if pivoted:
            findings = pivoted
            trace.append(
                make_event(
                    len(trace) + 1,
                    "synthesizer",
                    "synthesize",
                    "Built comparison table",
                    f"{len(findings)} entities",
                    "ok",
                )
            )

    return {"findings": findings, "trace": trace}
