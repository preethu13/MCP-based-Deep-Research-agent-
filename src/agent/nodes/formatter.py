"""Formatter node (F-04): render findings into the requested Markdown format."""

from __future__ import annotations

from typing import Any

from src.agent.state import AgentDeps, ResearchState, make_event


def formatter_node(state: ResearchState, deps: AgentDeps) -> dict[str, Any]:
    fmt = state.get("output_format", "brief")
    findings = state.get("findings", [])
    query = state.get("query", "Research findings")
    trace = list(state.get("trace", []))
    warnings = list(state.get("warnings", []))

    # Stage 6: Research Quality Validation Stage (QC-01..08)
    from src.agent.validator import validate_and_reconcile_research
    val_findings, verified_papers, val_warnings = validate_and_reconcile_research(findings, query)
    warnings.extend(val_warnings)

    trace.append(
        make_event(
            len(trace) + 1,
            "validator",
            "quality_audit",
            "Validated research quality",
            f"{len(verified_papers)} verified paper(s), {len(val_findings)} finding(s) audited",
            "ok" if verified_papers else "warn",
        )
    )

    output = deps.tools.format_output(val_findings, fmt, query=query)

    if warnings:
        notes = "\n".join(f"> - {w}" for w in warnings[:8])
        output += f"\n\n---\n\n> **Notes on this run**\n{notes}\n"

    trace.append(
        make_event(
            len(trace) + 1,
            "formatter",
            "format_output",
            f"Rendered {fmt}",
            f"{len(val_findings)} finding(s)",
            "ok",
        )
    )

    try:
        deps.sqlite.update_session_status(state["session_id"], "completed")
    except Exception:
        pass

    return {"final_output": output, "findings": val_findings, "warnings": warnings, "trace": trace}
