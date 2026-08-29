"""Planner node (AG-01): decompose a query into 2-5 sub-questions."""

from __future__ import annotations

import re
from typing import Any

from src.agent.state import AgentDeps, ResearchState, make_event

_SYSTEM = (
    "You are a meticulous research planner. Given a user's question, break it into "
    "2 to 5 focused, non-overlapping sub-questions that together fully answer it. "
    "Return ONLY a JSON array of strings, nothing else."
)


def _heuristic_decompose(query: str) -> list[str]:
    """Fallback decomposition when the LLM is unavailable or returns junk."""
    parts = re.split(r"\s+vs\.?\s+|\s+versus\s+|,\s*", query, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        return [f"What are the key characteristics and trade-offs of {p}?" for p in parts[:5]]
    return [query]


def planner_node(state: ResearchState, deps: AgentDeps) -> dict[str, Any]:
    query = state["query"]
    fmt = state.get("output_format", "brief")
    trace = list(state.get("trace", []))

    user = (
        f"User question: {query}\n"
        f"Desired output format: {fmt}.\n"
        "If the format is 'comparison', make each sub-question about one entity being compared."
    )

    sub_questions: list[str] = []
    try:
        data = deps.llm.complete_json(_SYSTEM, user)
        if isinstance(data, dict):
            data = data.get("sub_questions") or data.get("questions") or []
        sub_questions = [str(x).strip() for x in data if str(x).strip()][:5]
    except Exception:
        sub_questions = []

    if not sub_questions:
        sub_questions = _heuristic_decompose(query)

    trace.append(
        make_event(
            len(trace) + 1,
            "planner",
            "plan",
            "Decomposed the question",
            f"{len(sub_questions)} sub-question(s)",
            "ok",
        )
    )
    return {
        "sub_questions": sub_questions,
        "trace": trace,
        "research": [],
        "findings": [],
        "warnings": list(state.get("warnings", [])),
    }
