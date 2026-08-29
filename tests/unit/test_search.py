"""Unit tests for the ``web_search`` tool (no real network)."""

from __future__ import annotations

import src.tools.search as search_mod
from src.tools.search import web_search


class _FakeDDGS:
    """Context-manager stand-in for the ddgs client."""

    results = [
        {"title": "Result One", "href": "https://a.example/1", "body": "First body."},
        {"title": "", "href": "https://b.example/2", "body": "Second body."},
        {"title": "No URL", "href": "", "body": "dropped — no url"},
    ]

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def text(self, query, max_results=5):
        return self.results[:max_results]


def test_web_search_maps_fields(monkeypatch):
    monkeypatch.setattr(search_mod, "DDGS", _FakeDDGS)
    out = web_search("redis", max_results=5)
    assert out[0] == {
        "title": "Result One",
        "url": "https://a.example/1",
        "snippet": "First body.",
    }
    # Empty title falls back to the URL; result with no URL is dropped.
    assert out[1]["title"] == "https://b.example/2"
    assert all(r["url"] for r in out)
    assert len(out) == 2


def test_web_search_respects_max_results(monkeypatch):
    monkeypatch.setattr(search_mod, "DDGS", _FakeDDGS)
    assert len(web_search("redis", max_results=1)) == 1


def test_web_search_empty_query_returns_empty(monkeypatch):
    monkeypatch.setattr(search_mod, "DDGS", _FakeDDGS)
    assert web_search("   ") == []


def test_web_search_handles_missing_backend(monkeypatch):
    monkeypatch.setattr(search_mod, "DDGS", None)
    assert web_search("redis") == []


def test_web_search_never_raises(monkeypatch):
    class Boom:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            raise RuntimeError("network down")

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(search_mod, "DDGS", Boom)
    assert web_search("redis") == []
