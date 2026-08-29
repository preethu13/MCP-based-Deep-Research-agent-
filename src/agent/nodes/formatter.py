"""Formatter node (F-04): render findings into the requested Markdown format."""

from __future__ import annotations

from typing import Any

from src.agent.state import AgentDeps, ResearchState, make_event


def formatter_node(state: ResearchState, deps: AgentDeps) -> dict[str, Any]:
    fmt = state.get("output_format", "brief")
    findings = state.get("findings", [])
    query = state.get("query", "Research findings")
    trace = list(state.get("trace", []))

    output = deps.tools.format_output(findings, fmt, query=query)

    warnings = state.get("warnings", [])
    if warnings:
        notes = "\n".join(f"> - {w}" for w in warnings[:8])
        output += f"\n\n---\n\n> **Notes on this run**\n{notes}\n"

    trace.append(
        make_event(
            len(trace) + 1,
            "formatter",
            "format_output",
            f"Rendered {fmt}",
            f"{len(findings)} finding(s)",
            "ok",
        )
    )

    try:
        deps.sqlite.update_session_status(state["session_id"], "completed")
    except Exception:
        pass

    return {"final_output": output, "trace": trace}
