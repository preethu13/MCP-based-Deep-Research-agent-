"""LangGraph agent state and shared helpers."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, TypedDict


class ResearchState(TypedDict, total=False):
    """State threaded through the Plan -> Research -> Synthesize -> Format graph."""

    # inputs
    query: str
    output_format: str          # brief | comparison | report
    citation_style: str         # apa | mla
    session_id: str

    # working state
    sub_questions: list[str]
    research: list[dict[str, Any]]   # per sub-question: sources + memory hits
    findings: list[dict[str, Any]]   # finding dicts consumed by format_output

    # observability
    trace: list[dict[str, Any]]      # live "agent thinking" events (UI signature)
    warnings: list[str]
    metrics: dict[str, Any]          # execution timing and operational profiling metrics

    # output
    final_output: str


def make_event(
    step: int,
    node: str,
    tool: str,
    title: str,
    detail: str = "",
    status: str = "ok",
) -> dict[str, Any]:
    """Build one entry for the live research-log trace."""
    return {
        "step": step,
        "node": node,
        "tool": tool,
        "title": title,
        "detail": detail,
        "status": status,  # running | ok | warn | error
        "ts": time.time(),
    }


@dataclass
class AgentDeps:
    """Dependencies injected into every graph node (keeps nodes testable)."""

    llm: Any            # src.agent.llm.LLM
    tools: Any          # src.agent.tool_client.ToolClient
    sqlite: Any         # src.memory.sqlite_store.SQLiteStore
    settings: Any       # src.config.Settings
