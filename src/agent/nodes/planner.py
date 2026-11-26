"""Planner node (AG-01): decompose a query into 2-5 sub-questions."""

from __future__ import annotations

import re
from typing import Any

from src.agent.state import AgentDeps, ResearchState, make_event

_SYSTEM = (
    "You are an expert scientific research planner. Given a user's research topic, generate "
    "2 to 3 concise, highly focused academic sub-questions to guide literature retrieval.\n"
    "CRITICAL RULES:\n"
    "1. Every single sub-question MUST explicitly preserve the exact core topic phrase "
    "(e.g., if the topic is 'Context Rot', every sub-question must contain 'context rot').\n"
    "2. Do NOT dilute the topic with unrelated domains, generic buzzwords, or broad questions.\n"
    "3. Structure the sub-questions around: (a) definition and mechanisms, "
    "(b) empirical performance impact and causes, and (c) mitigation strategies or architectures.\n"
    "4. Return ONLY a JSON array of 2 to 3 question strings, nothing else."
)


def _heuristic_decompose(query: str) -> list[str]:
    """Fallback decomposition when the LLM is unavailable or returns junk."""
    clean_topic = re.sub(
        r"^(what\s+is|what\s+are|how\s+does|how\s+do|why\s+is|why\s+are|tell\s+me\s+about)\s+",
        "",
        query.strip(),
        flags=re.IGNORECASE
    ).rstrip("?").strip() or query.strip()

    is_comparison = bool(re.search(r"\b(vs|versus|compare|comparison|difference|between)\b", clean_topic, re.IGNORECASE))
    if is_comparison:
        return [
            f"What are the core definitions, architectures, and mechanisms of {clean_topic}?",
            f"What are the key technical differences and trade-offs in {clean_topic}?",
            f"What are the primary use cases, advantages, and limitations of {clean_topic}?",
        ]

    return [
        f"What is the definition and core mechanism of {clean_topic}?",
        f"What are the key methodologies, architectures, and implementations of {clean_topic}?",
        f"What are the primary applications, performance benefits, and best practices for {clean_topic}?",
    ]


def planner_node(state: ResearchState, deps: AgentDeps) -> dict[str, Any]:
    query = state["query"]
    fmt = state.get("output_format", "brief")
    trace = list(state.get("trace", []))

    user = (
        f"User question: {query}\n"
        f"Desired format: {fmt}.\n"
        "Return ONLY a JSON array of 2 to 3 concise sub-questions."
    )

    sub_questions: list[str] = []
    try:
        data = deps.llm.complete_json(_SYSTEM, user, max_tokens=90)
        if isinstance(data, dict):
            data = data.get("sub_questions") or data.get("questions") or []
        sub_questions = [str(x).strip() for x in data if str(x).strip()][:3]
    except Exception:
        sub_questions = []

    if not sub_questions:
        sub_questions = _heuristic_decompose(query)[:3]

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
