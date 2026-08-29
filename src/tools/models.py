"""Shared pydantic models for MCP tools."""

from __future__ import annotations

from pydantic import BaseModel


class SearchResult(BaseModel):
    """A single web search hit."""

    title: str
    url: str
    snippet: str
