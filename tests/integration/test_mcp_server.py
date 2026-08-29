"""Integration test: exercise the tools over a real in-memory MCP round-trip.

Uses FastMCP's in-memory client transport, which invokes the actual registered
tool functions in-process — proving the MCP surface works without spawning a
subprocess.  Only network-free / Ollama-free tools are called here.
"""

from __future__ import annotations

import pytest

fastmcp = pytest.importorskip("fastmcp")
from fastmcp import Client  # noqa: E402

from src.mcp_server import mcp  # noqa: E402


def _text(result) -> str:
    """Extract a string payload from a FastMCP CallToolResult across versions."""
    data = getattr(result, "data", None)
    if isinstance(data, str):
        return data
    content = getattr(result, "content", None)
    if content and hasattr(content[0], "text"):
        return content[0].text
    return str(data if data is not None else result)


async def test_mcp_lists_all_six_tools():
    async with Client(mcp) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools}
    assert {
        "web_search",
        "scrape_page",
        "generate_citation",
        "store_memory",
        "recall_memory",
        "format_output",
    } <= names


async def test_mcp_generate_citation_roundtrip():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "generate_citation",
            {
                "source": {
                    "url": "https://redis.io",
                    "title": "Redis",
                    "author": "Jane Doe",
                    "year": 2024,
                },
                "style": "apa",
            },
        )
    text = _text(result)
    assert "Doe, J. (2024)." in text
    assert "*Redis*" in text


async def test_mcp_format_output_roundtrip():
    findings = [{"claim": "Redis is fast.", "citations": [], "sources": []}]
    async with Client(mcp) as client:
        result = await client.call_tool("format_output", {"findings": findings, "format": "brief"})
    text = _text(result)
    assert "# Research Brief" in text
    assert "Redis is fast." in text
