"""Unit tests for the ``scrape_page`` tool and its HTML extraction."""

from __future__ import annotations

import src.tools.scrape as scrape_mod
from src.tools.scrape import _extract_text, scrape_page


class _Resp:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code


_ARTICLE = """
<html><head><title>  Redis Overview </title></head>
<body>
  <nav>menu menu menu</nav>
  <script>var x = 1;</script>
  <style>.a{color:red}</style>
  <article><p>Redis is an in-memory data structure store widely used as a database, cache,
  and message broker. It supports data structures such as strings, hashes, lists, sets,
  sorted sets with range queries, bitmaps, hyperloglogs, geospatial indexes and streams.
  Redis is open source and written in ANSI C. It works in most POSIX systems like Linux,
  *BSD, OS X without external dependencies. Redis has built-in replication, Lua scripting,
  LRU eviction, transactions and different levels of on-disk persistence.</p>
  </article>
  <footer>copyright</footer>
</body></html>
"""



def test_extract_text_strips_chrome_and_scripts():
    title, text = _extract_text(_ARTICLE)
    assert title == "Redis Overview"
    assert "in-memory data structure store" in text
    assert "var x" not in text          # script stripped
    assert "menu menu" not in text      # nav stripped
    assert "copyright" not in text      # footer stripped


def test_scrape_rejects_non_http():
    result = scrape_page("ftp://nope", respect_robots=False)
    assert result["method_used"] == "failed"
    assert "error" in result


def test_scrape_static_success(monkeypatch):
    monkeypatch.setattr(scrape_mod.httpx, "get", lambda *a, **k: _Resp(_ARTICLE))
    result = scrape_page("https://example.com/redis", respect_robots=False)
    assert result["method_used"] == "static"
    assert result["title"] == "Redis Overview"
    assert result["word_count"] > 5
    assert "error" not in result


def test_scrape_http_error(monkeypatch):
    monkeypatch.setattr(scrape_mod.httpx, "get", lambda *a, **k: _Resp("", status_code=404))
    result = scrape_page("https://example.com/missing", respect_robots=False)
    assert result["error"] == "HTTP 404"
    assert result["method_used"] == "failed"


def test_scrape_blocked_by_robots(monkeypatch):
    monkeypatch.setattr(scrape_mod, "_robots_allows", lambda *a, **k: False)
    result = scrape_page("https://example.com/secret", respect_robots=True)
    assert result["method_used"] == "blocked"
    assert "robots" in result["error"]


def test_scrape_thin_content_without_playwright(monkeypatch):
    monkeypatch.setattr(
        scrape_mod.httpx, "get", lambda *a, **k: _Resp("<html><body>tiny</body></html>")
    )
    monkeypatch.setattr(scrape_mod, "_render_with_playwright", lambda *a, **k: None)
    result = scrape_page("https://example.com/spa", respect_robots=False)
    assert result["method_used"] == "static_thin"


def test_scrape_fetch_exception_returns_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(scrape_mod.httpx, "get", boom)
    result = scrape_page("https://example.com/x", respect_robots=False)
    assert result["method_used"] == "failed"
    assert "connection reset" in result["error"]
