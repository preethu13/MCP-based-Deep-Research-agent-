"""``scrape_page`` tool (MCP-02).

Fetches a URL and extracts clean, readable text.  Order of operations:

1. Respect ``robots.txt`` (configurable) — refuse disallowed URLs (security 3.4).
2. Static fetch with ``httpx`` + parse with BeautifulSoup, stripping scripts,
   styles and chrome so no executable content reaches the LLM (security 3.4 / FC-04).
3. If static extraction yields < 200 chars, fall back to Playwright rendering
   for JS-heavy pages.  Playwright is imported lazily and optional — if it is
   not installed the thin static result is returned rather than crashing.

The tool never raises; failures come back as a structured dict with an
``error`` key (MCP-07 / FC-05).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

_STRIP_TAGS = ["script", "style", "noscript", "template", "svg", "form"]
_CHROME_TAGS = ["nav", "header", "footer", "aside"]
_MIN_USABLE_CHARS = 200


def _robots_allows(url: str, user_agent: str, timeout: int) -> bool:
    """Return True if robots.txt permits fetching ``url`` (fail-open on error)."""
    try:
        parts = urlparse(url)
        robots_url = urljoin(f"{parts.scheme}://{parts.netloc}", "/robots.txt")
        resp = httpx.get(robots_url, timeout=min(timeout, 2), follow_redirects=True)
        if resp.status_code >= 400:
            return True  # no usable robots.txt -> allowed
        parser = RobotFileParser()
        parser.parse(resp.text.splitlines())
        return parser.can_fetch(user_agent, url)
    except Exception:
        return True  # never let robots checking block the pipeline on error


def _extract_text(html: str) -> tuple[str, str]:
    """Return ``(title, cleaned_text)`` from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_STRIP_TAGS + _CHROME_TAGS):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""

    main = soup.find("article") or soup.find("main") or soup.body or soup
    text = main.get_text(separator=" ", strip=True)
    # Collapse runs of whitespace introduced by nested markup.
    text = " ".join(text.split())
    return title, text


def _render_with_playwright(url: str, user_agent: str, timeout: int) -> str | None:
    """Render a JS page headlessly.  Returns HTML, or None if unavailable."""
    try:
        from playwright.sync_api import sync_playwright  # lazy, optional
    except Exception:
        return None
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=user_agent)
                page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
                html = page.content()
            finally:
                browser.close()
        return html
    except Exception:
        return None


def scrape_page(
    url: str,
    timeout: int = 8,
    user_agent: str = "DeepResearchAgent/1.0",
    respect_robots: bool = True,
    enable_playwright: bool = True,
) -> dict[str, Any]:
    """Fetch and extract clean text content from a web page.

    Returns:
        dict with keys ``url``, ``title``, ``text``, ``word_count``,
        ``method_used`` — or the same shape with an ``error`` key on failure.
    """
    result: dict[str, Any] = {
        "url": url,
        "title": "",
        "text": "",
        "word_count": 0,
        "method_used": "none",
    }

    if not url or not urlparse(url).scheme.startswith("http"):
        result.update(error="invalid or non-http URL", method_used="failed")
        return result

    if respect_robots and not _robots_allows(url, user_agent, timeout):
        result.update(error="disallowed by robots.txt", method_used="blocked")
        return result

    # --- static fetch ---
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": user_agent},
            timeout=timeout,
            follow_redirects=True,
        )
        if resp.status_code >= 400:
            result.update(error=f"HTTP {resp.status_code}", method_used="failed")
            return result
        title, text = _extract_text(resp.text)
        result.update(title=title, text=text, method_used="static")
    except Exception as exc:
        result.update(error=f"fetch failed: {exc}", method_used="failed")
        return result

    # --- Playwright fallback for thin/JS pages (only if explicitly enabled) ---
    if enable_playwright and len(result["text"]) < _MIN_USABLE_CHARS:
        html = _render_with_playwright(url, user_agent, timeout)
        if html:
            title, text = _extract_text(html)
            if len(text) > len(result["text"]):
                result.update(title=title or result["title"], text=text, method_used="playwright")
        else:
            result["method_used"] = "static_thin"

    result["word_count"] = len(result["text"].split())
    return result
