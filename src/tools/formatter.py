"""``format_output`` tool (MCP-06, F-04, OUT-01..04).

Renders a list of findings into one of three Markdown formats — Brief,
Comparison Chart, or Insight Report — each ending in a numbered References
section with full citations in the requested style.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Literal

from src.agent.validator import validate_and_reconcile_research

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
    for i, cite in enumerate(ordered, start=1):
        lines.append(f"{i}. {cite}")
    return "\n".join(lines) + "\n"


def _render_papers_section(papers: list[dict[str, Any]]) -> list[str]:
    """Format academic papers with direct links, verified publication status, and evidence tiers."""
    if not papers:
        return [
            "## Research Papers & Literature",
            "",
            "_No peer-reviewed papers or scientific preprints met the relevance threshold for this query._",
            "",
        ]

    peer_count = sum(1 for p in papers if p.get("is_peer_reviewed"))
    preprint_count = sum(1 for p in papers if "preprint" in str(p.get("publication_status", "")).lower())

    lines = [
        "## Research Papers & Literature",
        "",
        f"The following {len(papers)} paper(s) and scientific studies were analyzed ({peer_count} peer-reviewed, {preprint_count} preprints):",
        "",
    ]
    for i, paper in enumerate(papers, start=1):
        title = paper.get("title") or "Untitled Paper"
        url = paper.get("url") or ""
        pdf_url = paper.get("pdf_url") or ""
        author = paper.get("author_short") or paper.get("author") or "Authors not listed"
        year = paper.get("year") or "n.d."
        venue = paper.get("venue") or ""
        pub_status = paper.get("publication_status") or "Unknown publication status"
        tier = paper.get("evidence_tier") or "Supporting evidence"
        summary = (paper.get("summary") or paper.get("abstract") or "No abstract available.").strip()

        # Clickable title header
        title_md = f"[{title}]({url})" if url else title
        lines.append(f"### {i}. {title_md}")

        meta_parts = [
            f"**Status:** *{pub_status}*",
            f"**Evidence Tier:** *{tier}*",
            f"**Year:** {year}",
        ]
        if venue and venue != "Venue unavailable":
            meta_parts.append(f"**Venue:** {venue}")
        lines.append(" | ".join(meta_parts))
        lines.append(f"**Authors:** {author}")
        lines.append("")

        link_parts = []
        if url:
            link_parts.append(f"[View Paper / DOI]({url})")
        if pdf_url and pdf_url != url:
            link_parts.append(f"[Direct PDF]({pdf_url})")
        if link_parts:
            lines.append(" · ".join(link_parts))
            lines.append("")

        lines.append(f"**Abstract & Core Contributions:**")
        lines.append(f"> {summary}")
        lines.append("")

    return lines


def _first_sentence(text: str) -> str:
    for sep in (". ", "? ", "! "):
        if sep in text:
            return text.split(sep)[0].strip() + sep.strip()
    return text.strip()


def _render_brief(findings, query, generated_on, papers, ordered, index) -> str:
    lines = [
        f"# Research Brief: {query}",
        f"*Deep Research Agent · {generated_on:%B %d, %Y}*",
        "",
        "## Key Findings",
        "",
    ]
    for i, finding in enumerate(findings, start=1):
        sub_q = finding.get("sub_question")
        claim = finding.get("claim", "").strip()
        marker = _markers(finding, index)
        if marker and not re.search(r"\[\d+\]", claim):
            claim = f"{claim} {marker}"
        if sub_q:
            lines.append(f"### {sub_q}\n")
            lines.append(f"{claim}\n")
        else:
            lines.append(f"- {claim}\n")
    lines.append("")

    if papers:
        lines += _render_papers_section(papers)

    lines += [_render_references(ordered)]
    return "\n".join(lines)


def _render_report(findings, query, generated_on, papers, ordered, index) -> str:
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
    ]

    if papers:
        lines += _render_papers_section(papers)

    lines += ["## Findings", ""]
    for finding in findings:
        sub_q = finding.get("sub_question") or "Finding"
        claim = finding.get("claim", "").strip()
        marker = _markers(finding, index)
        if marker and not re.search(r"\[\d+\]", claim):
            claim = f"{claim} {marker}"
        lines += [f"### {sub_q}", "", f"{claim}", ""]

    lines.append(_render_references(ordered))
    return "\n".join(lines)


def _render_comparison(findings, query, generated_on, papers, ordered, index) -> str:
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

        header = "| Dimension | " + " | ".join(names) + " |"
        sep = "| " + " | ".join(["---"] * (len(names) + 1)) + " |"
        lines += [header, sep]
        for attr in attrs:
            row = [attr] + [f.get("attributes", {}).get(attr, "-") for f in entities]
            lines.append("| " + " | ".join(row) + " |")

        sources_row = ["Sources"] + [_markers(f, index) or "-" for f in entities]
        lines.append("| " + " | ".join(sources_row) + " |")
        lines.append("")
    else:
        lines += [
            "| Sub-question | Finding | Sources |",
            "| --- | --- | --- |",
        ]
        for f in findings:
            q = f.get("sub_question") or "-"
            c = f.get("claim") or "-"
            m = _markers(f, index) or "-"
            lines.append(f"| {q} | {c} | {m} |")
        lines.append("")

    if papers:
        lines += _render_papers_section(papers)

    lines += [_render_references(ordered)]
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

    # Run research quality validation and reconciliation
    validated_findings, verified_papers, _ = validate_and_reconcile_research(findings, query)

    # If verified papers exist, synchronize bibliography 1:1 with verified papers
    if verified_papers:
        ordered = [p["citation_str"] for p in verified_papers if "citation_str" in p]
        index = {cite: idx for idx, cite in enumerate(ordered, start=1)}
    else:
        ordered, index = _collect_references(validated_findings)

    if format == "comparison":
        return _render_comparison(validated_findings, query, generated_on, verified_papers, ordered, index)
    if format == "report":
        return _render_report(validated_findings, query, generated_on, verified_papers, ordered, index)
    return _render_brief(validated_findings, query, generated_on, verified_papers, ordered, index)
