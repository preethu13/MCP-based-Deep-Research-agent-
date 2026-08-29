"""``format_output`` tool (MCP-06, F-04, OUT-01..04).

Renders a list of findings into one of three Markdown formats — Brief,
Comparison Chart, or Insight Report — each ending in a numbered References
section with full citations in the requested style.

Finding dict schema (all keys optional except ``claim``)::

    {
        "sub_question": str,
        "claim": str,
        "citations": [str],          # pre-formatted APA/MLA strings
        "sources": [{"url", "title"}],
        "entity": str | None,        # comparison rows
        "attributes": {str: str},    # comparison columns
        "confidence": float,
    }
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

OutputFormat = Literal["brief", "comparison", "report"]


def _collect_references(findings: list[dict[str, Any]]) -> tuple[list[str], dict[str, int]]:
    """Return an ordered, de-duplicated reference list and a citation->index map."""
    ordered: list[str] = []
    index: dict[str, int] = {}
    for finding in findings:
        for citation in finding.get("citations", []) or []:
            if citation not in index:
                ordered.append(citation)
                index[citation] = len(ordered)  # 1-based
    return ordered, index


def _markers(finding: dict[str, Any], index: dict[str, int]) -> str:
    nums = sorted({index[c] for c in finding.get("citations", []) or [] if c in index})
    return "".join(f"[{n}]" for n in nums)


def _render_references(ordered: list[str]) -> str:
    if not ordered:
        return "## References\n\n_No sources were cited._\n"
    lines = ["## References", ""]
    lines += [f"{i}. {cite}" for i, cite in enumerate(ordered, start=1)]
    return "\n".join(lines) + "\n"


def _first_sentence(text: str) -> str:
    for sep in (". ", "? ", "! "):
        if sep in text:
            return text.split(sep)[0].strip() + sep.strip()
    return text.strip()


def _render_brief(findings, query, generated_on, ordered, index) -> str:
    lines = [
        f"# Research Brief — {query}",
        f"*Deep Research Agent · {generated_on:%B %d, %Y}*",
        "",
        "## Key findings",
        "",
    ]
    for finding in findings:
        marker = _markers(finding, index)
        claim = finding.get("claim", "").strip()
        suffix = f" {marker}" if marker else ""
        lines.append(f"- {claim}{suffix}")
    lines += ["", _render_references(ordered)]
    return "\n".join(lines)


def _render_report(findings, query, generated_on, ordered, index) -> str:
    summary_bits = [_first_sentence(f.get("claim", "")) for f in findings if f.get("claim")]
    summary = " ".join(summary_bits[:3]) or "No findings were produced for this query."
    lines = [
        f"# {query}",
        f"*Insight Report · Deep Research Agent · {generated_on:%B %d, %Y}*",
        "",
        "## Executive summary",
        "",
        f"This report addresses {len(findings)} sub-question(s). {summary}",
        "",
        "## Findings",
        "",
    ]
    for finding in findings:
        sub_q = finding.get("sub_question") or "Finding"
        marker = _markers(finding, index)
        claim = finding.get("claim", "").strip()
        suffix = f" {marker}" if marker else ""
        lines += [f"### {sub_q}", "", f"{claim}{suffix}", ""]
    lines.append(_render_references(ordered))
    return "\n".join(lines)


def _render_comparison(findings, query, generated_on, ordered, index) -> str:
    lines = [
        f"# Comparison — {query}",
        f"*Comparison Chart · Deep Research Agent · {generated_on:%B %d, %Y}*",
        "",
    ]
    entities = [f for f in findings if f.get("entity") and f.get("attributes")]

    if len(entities) >= 2:
        names = [f["entity"] for f in entities]
        attrs: list[str] = []
        for f in entities:
            for key in f["attributes"]:
                if key not in attrs:
                    attrs.append(key)

        lines.append("| Dimension | " + " | ".join(names) + " |")
        lines.append("|" + "---|" * (len(names) + 1))
        for attr in attrs:
            row = [str(f["attributes"].get(attr, "—")) for f in entities]
            lines.append(f"| {attr} | " + " | ".join(row) + " |")
        # Sources row so every column is traceable.
        src_row = [_markers(f, index) or "—" for f in entities]
        lines.append("| Sources | " + " | ".join(src_row) + " |")
    else:
        # Fallback: no structured entities -> question/finding table.
        lines.append("| Sub-question | Finding | Sources |")
        lines.append("|---|---|---|")
        for finding in findings:
            sub_q = (finding.get("sub_question") or "—").replace("|", "\\|")
            claim = finding.get("claim", "").replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {sub_q} | {claim} | {_markers(finding, index) or '—'} |")

    lines += ["", _render_references(ordered)]
    return "\n".join(lines)


def format_output(
    findings: list[dict[str, Any]],
    format: OutputFormat = "brief",
    query: str = "Research findings",
    generated_on: date | None = None,
) -> str:
    """Render ``findings`` into a Brief, Comparison Chart, or Insight Report."""
    generated_on = generated_on or date.today()

    if not findings:
        return (
            f"# {query}\n\n"
            f"*Deep Research Agent · {generated_on:%B %d, %Y}*\n\n"
            "No findings were produced for this query. This can happen when no "
            "sources were reachable or the topic returned no results — try "
            "rephrasing the question or checking your connection.\n"
        )

    ordered, index = _collect_references(findings)

    if format == "comparison":
        return _render_comparison(findings, query, generated_on, ordered, index)
    if format == "report":
        return _render_report(findings, query, generated_on, ordered, index)
    return _render_brief(findings, query, generated_on, ordered, index)
