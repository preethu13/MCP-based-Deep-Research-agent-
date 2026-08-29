"""Unit tests for APA-7 and MLA-9 citation formatting."""

from __future__ import annotations

from datetime import date

from src.tools.citation import generate_citation

_ACCESSED = date(2026, 3, 15)


def test_apa_with_author_and_year():
    cite = generate_citation(
        {
            "url": "https://redis.io/docs",
            "title": "Redis Documentation",
            "author": "Jane Doe",
            "publisher": "Redis Ltd.",
            "year": 2024,
        },
        "apa",
        accessed_date=_ACCESSED,
    )
    assert cite == "Doe, J. (2024). *Redis Documentation*. Redis Ltd. https://redis.io/docs"


def test_apa_without_date_uses_nd_and_retrieval():
    cite = generate_citation(
        {"url": "https://example.com/x", "title": "A Page"}, "apa", accessed_date=_ACCESSED
    )
    assert "(n.d.)." in cite
    assert "Retrieved March 15, 2026, from https://example.com/x" in cite


def test_mla_with_author():
    cite = generate_citation(
        {
            "url": "https://redis.io/docs",
            "title": "Redis Documentation",
            "author": "Jane Doe",
            "publisher": "Redis Ltd.",
            "year": 2024,
        },
        "mla",
        accessed_date=_ACCESSED,
    )
    assert cite.startswith('Doe, Jane. "Redis Documentation." *Redis Ltd.*, 2024,')
    assert cite.endswith("Accessed 15 March 2026.")


def test_site_name_derived_from_url_without_www():
    cite = generate_citation(
        {"url": "https://www.nginx.com/blog", "title": "Caching"}, "apa", accessed_date=_ACCESSED
    )
    assert "nginx.com" in cite
    # The site name part should not use www. — but the URL itself may contain it.
    # Split on the URL to isolate the site name portion for the assertion.
    site_part = cite.split("https://")[0]
    assert "www." not in site_part



def test_missing_title_becomes_untitled():
    cite = generate_citation({"url": "https://x.example"}, "apa", accessed_date=_ACCESSED)
    assert "*Untitled*" in cite


def test_org_author_passed_through():
    cite = generate_citation(
        {"url": "https://who.int", "title": "Report", "author": "WHO", "year": 2023}, "mla",
        accessed_date=_ACCESSED,
    )
    assert cite.startswith("WHO.")


def test_title_wrapped_in_markdown_italics():
    cite = generate_citation(
        {"url": "https://x.example", "title": "Hello"}, "apa", accessed_date=_ACCESSED
    )
    assert "*Hello*" in cite
