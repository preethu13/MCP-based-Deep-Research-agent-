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

_SYNTH_SYSTEM = (
    "You are an expert research analyst. Your goal is to write a clear, factual, "
    "and informative 2-4 sentence key finding that directly answers the sub-question "
    "using the provided research sources and snippets.\n"
    "Guidelines:\n"
    "1. Extract core facts, technologies, benefits, or trade-offs mentioned in the sources.\n"
    "2. Be direct, authoritative, and concise.\n"
    "3. Do NOT meta-comment on source quality, grammar, or missing web pages.\n"
    "4. Do NOT output citation brackets like [1] or references; those are formatted automatically."
)

_COMPARE_SYSTEM = (
    "You convert research notes into a structured comparison. Return ONLY JSON of "
    'the form {"dimensions": ["..."], "entities": [{"name": "...", "attributes": '
    '{"dimension": "short value"}}]}. Compare every entity across the same '
    "dimensions. Keep values short (a few words)."
)


def _synthesize_claim(llm: Any, sub_q: str, context: str) -> str:
    user = f"Sub-question: {sub_q}\n\nSources:\n{context}"
    try:
        claim = llm.complete(_SYNTH_SYSTEM, user).strip()
        return claim or f"The sources did not yield a clear answer to: {sub_q}."
    except Exception:
        # LLM unreachable mid-run — degrade instead of crashing (FC-05/FC-07).
        snippet = context[:300].replace("\n", " ")
        return f"(Unverified) Based on the gathered sources: {snippet}…"


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
    findings: list[dict[str, Any]] = []
    trace = list(state.get("trace", []))

    for item in state.get("research", []):
        sub_q = item["sub_question"]
        sources = item.get("sources", [])
        memory_hits = item.get("memory_hits", [])

        context_parts = [
            f"[{i}] {s['title']}\nURL: {s['url']}\n{s['text']}"
            for i, s in enumerate(sources, start=1)
        ]
        context_parts += [f"[memory] {m['content']}" for m in memory_hits]
        context = "\n\n".join(context_parts)

        if not sources and not memory_hits:
            findings.append(
                {
                    "sub_question": sub_q,
                    "claim": f"No reliable sources were found for: {sub_q}.",
                    "citations": [],
                    "sources": [],
                    "confidence": 0.1,
                }
            )
            trace.append(
                make_event(
                    len(trace) + 1, "synthesizer", "synthesize", "No sources", sub_q[:80], "warn"
                )
            )
            continue

        claim = _synthesize_claim(deps.llm, sub_q, context)
        citations = [deps.tools.generate_citation(s, style) for s in sources]
        used_sources = [{"url": s["url"], "title": s["title"]} for s in sources]

        finding = {
            "sub_question": sub_q,
            "claim": claim,
            "citations": citations,
            "sources": used_sources,
            "confidence": 0.9 if sources else 0.5,
        }
        _persist(deps, state["session_id"], finding)

        # AG-06: store the finding for future cross-session recall.
        deps.tools.store_memory(
            state["session_id"], f"Q: {sub_q}\nA: {claim}", {"topic": sub_q[:120]}
        )

        trace.append(
            make_event(
                len(trace) + 1,
                "synthesizer",
                "synthesize",
                "Synthesized a grounded finding",
                f"{len(citations)} citation(s)",
                "ok",
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
