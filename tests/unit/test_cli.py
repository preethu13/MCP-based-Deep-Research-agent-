"""Tests for the Typer CLI, driven fully offline via demo mode."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

import src.agent.tool_client as tool_client_mod
from src.cli.main import app
from src.config import get_settings

runner = CliRunner()


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    """Point storage at a temp dir and stub the network tools."""
    monkeypatch.setenv("RESEARCH_DB_PATH", str(tmp_path / "research.db"))
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "agent.log"))
    get_settings.cache_clear()

    monkeypatch.setattr(
        tool_client_mod,
        "_web_search",
        lambda query, max_results=5, timeout=10, **k: [
            {"title": "Redis", "url": "https://ok.example/redis", "snippet": "Redis is in-memory."}
        ],
    )
    monkeypatch.setattr(
        tool_client_mod,
        "_scrape_page",
        lambda url, **k: {
            "url": url, "title": "Redis", "text": "Redis is an in-memory store. " * 20,
            "word_count": 60, "method_used": "static",
        },
    )
    yield tmp_path
    get_settings.cache_clear()


def test_ask_demo_offline(cli_env):
    result = runner.invoke(app, ["ask", "What is Redis?", "--demo", "-f", "brief"])
    assert result.exit_code == 0, result.output
    assert "References" in result.output


def test_sessions_list_after_ask(cli_env):
    runner.invoke(app, ["ask", "What is Redis?", "--demo"])
    result = runner.invoke(app, ["sessions", "list"])
    assert result.exit_code == 0
    assert "Research sessions" in result.output


def test_export_after_ask(cli_env, tmp_path):
    runner.invoke(app, ["ask", "What is Redis?", "--demo"])
    out_file = tmp_path / "out.md"
    result = runner.invoke(app, ["export", "-o", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    assert "Research Brief" in out_file.read_text(encoding="utf-8")


def test_export_with_no_sessions_exits_nonzero(cli_env):
    result = runner.invoke(app, ["export", "-o", str(cli_env / "none.md")])
    assert result.exit_code == 1


def test_sessions_delete_missing(cli_env):
    result = runner.invoke(app, ["sessions", "delete", "does-not-exist"])
    assert result.exit_code == 0
    assert "No such session" in result.output


def test_doctor_runs_offline(cli_env):
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Environment check" in result.output
