"""Unit tests for the three output formats and reference handling."""

from __future__ import annotations

from datetime import date

from src.tools.formatter import format_output

_ON = date(2026, 3, 15)

_FINDINGS = [
    {
        "sub_question": "What is Redis?",
        "claim": "Redis is an in-memory data store.",
        "citations": ["Doe, J. (2024). *Redis*. redis.io. https://redis.io"],
        "sources": [{"url": "https://redis.io", "title": "Redis"}],
    },
    {
        "sub_question": "What is Memcached?",
        "claim": "Memcached is a distributed cache.",
        "citations": ["Roe, A. (2023). *Memcached*. memcached.org. https://memcached.org"],
        "sources": [{"url": "https://memcached.org", "title": "Memcached"}],
    },
]


def test_empty_findings_message():
    out = format_output([], "brief", query="Nothing", generated_on=_ON)
    assert "No findings were produced" in out
    assert "Nothing" in out


def test_brief_has_bullets_markers_and_references():
    out = format_output(_FINDINGS, "brief", query="Caches", generated_on=_ON)
    assert "# Research Brief — Caches" in out
    assert "- Redis is an in-memory data store. [1]" in out
    assert "- Memcached is a distributed cache. [2]" in out
    assert "## References" in out
    assert "1. Doe, J. (2024)." in out
    assert "2. Roe, A. (2023)." in out


def test_report_has_summary_and_sections():
    out = format_output(_FINDINGS, "report", query="Caches", generated_on=_ON)
    assert "*Insight Report" in out
    assert "## Executive summary" in out
    assert "### What is Redis?" in out
    assert "### What is Memcached?" in out


def test_comparison_structured_table():
    findings = [
        {"entity": "Redis", "claim": "Redis", "attributes": {"Overview": "in-memory", "Speed": "fast"},
         "citations": ["c1"], "sources": []},
        {"entity": "Memcached", "claim": "Memcached", "attributes": {"Overview": "cache", "Speed": "fast"},
         "citations": ["c1"], "sources": []},
    ]
    out = format_output(findings, "comparison", query="Redis vs Memcached", generated_on=_ON)
    assert "| Dimension | Redis | Memcached |" in out
    assert "| Overview | in-memory | cache |" in out
    assert "| Sources |" in out
    # Shared citation de-duplicated to a single reference.
    assert out.count("1. c1") == 1


def test_comparison_falls_back_to_question_table():
    out = format_output(_FINDINGS, "comparison", query="Caches", generated_on=_ON)
    assert "| Sub-question | Finding | Sources |" in out
    assert "What is Redis?" in out


def test_references_are_deduplicated():
    shared = "Same, S. (2024). *Shared*. x.example. https://x.example"
    findings = [
        {"claim": "A.", "citations": [shared], "sources": []},
        {"claim": "B.", "citations": [shared], "sources": []},
    ]
    out = format_output(findings, "brief", query="Q", generated_on=_ON)
    assert out.count(shared) == 1
    assert "- A. [1]" in out
    assert "- B. [1]" in out
