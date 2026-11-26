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
    for i, cite in enumerate(ordered, start=1):
        lines.append(f"{i}. {cite}")
    return "\n".join(lines) + "\n"


def _collect_papers(findings: list[dict[str, Any]], query: str = "") -> list[dict[str, Any]]:
    """Extract distinct verified paper objects from findings."""
    from src.tools.search import RELEVANCE_THRESHOLD, is_candidate_relevant, score_paper_relevance

    seen_urls = set()
    papers: list[dict[str, Any]] = []
    for f in findings:
        sub_q = f.get("sub_question") or ""
        for p in f.get("papers", []) or []:
            url = p.get("url", "")
            title = p.get("title", "")
            if (url or title) and url not in seen_urls:
                # Final check: only include verified papers matching query relevance
                if query and not is_candidate_relevant(p, query, sub_q):
                    continue
                if url:
                    seen_urls.add(url)
                papers.append(p)
    return papers


def _render_papers_section(papers: list[dict[str, Any]]) -> list[str]:
    """Format academic papers with direct links, authors, year, and detailed summaries."""
    if not papers:
        return [
            "## Research Papers & Literature",
            "",
            "_No peer-reviewed papers met the relevance threshold for this query._",
            "",
        ]

    lines = [
        "## Research Papers & Literature",
        "",
        f"The following {len(papers)} peer-reviewed paper(s) and scientific studies were analyzed:",
        "",
    ]
    for i, paper in enumerate(papers, start=1):
        title = paper.get("title") or "Untitled Paper"
        url = paper.get("url") or ""
        pdf_url = paper.get("pdf_url") or ""
        author = paper.get("author") or ", ".join(paper.get("authors", [])[:3]) or "Authors not listed"
        year = paper.get("year") or "n.d."
        venue = paper.get("venue") or ""
        summary = (paper.get("summary") or paper.get("abstract") or "No abstract available.").strip()

        # Clickable title header
        title_md = f"[{title}]({url})" if url else title
        lines.append(f"### {i}. 📄 {title_md}")

        meta_parts = [f"**Authors:** {author}", f"**Year:** {year}"]
        if venue:
            meta_parts.append(f"**Venue:** {venue}")
        lines.append(" | ".join(meta_parts))
        lines.append("")

        link_parts = []
        if url:
            link_parts.append(f"[🔗 View Paper / DOI]({url})")
        if pdf_url and pdf_url != url:
            link_parts.append(f"[📥 Direct PDF]({pdf_url})")
        if link_parts:
            lines.append(" · ".join(link_parts))
            lines.append("")

        lines.append(f"**Summary & Key Contributions:**")
        lines.append(f"> {summary}")
        lines.append("")

    return lines


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
        if not claim:
            sub_q = finding.get("sub_question", "")
            claim = f"Insufficient direct evidence in retrieved sources to establish findings for: {sub_q}" if sub_q else "Finding could not be synthesized from available sources."
        suffix = f" {marker}" if marker else ""
        lines.append(f"- {claim}{suffix}")
    lines.append("")

    papers = _collect_papers(findings, query)
    if papers:
        lines += _render_papers_section(papers)

    lines += [_render_references(ordered)]
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
    ]

    papers = _collect_papers(findings, query)
    if papers:
        lines += _render_papers_section(papers)

    lines += [
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

    lines.append("")
    papers = _collect_papers(findings, query)
    if papers:
        lines += _render_papers_section(papers)

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
