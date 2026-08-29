"""End-to-end smoke test — requires a running Ollama and network access.

Deselected by default in CI via ``-m 'not e2e'``.  Run explicitly with::

    pytest -m e2e
"""

from __future__ import annotations

import pytest

from src.agent.llm import OllamaLLM
from src.config import get_settings

pytestmark = pytest.mark.e2e


def _ollama_ready() -> bool:
    settings = get_settings()
    ok, _ = OllamaLLM(settings.chat_model, settings.ollama_host).ping()
    return ok


@pytest.mark.skipif(not _ollama_ready(), reason="Ollama not reachable")
def test_live_research_brief(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_DB_PATH", str(tmp_path / "e2e.db"))
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma"))
    get_settings.cache_clear()

    from src.agent.graph import ResearchAgent

    agent = ResearchAgent.from_settings()
    state = agent.run("What is the capital of France?", "brief", "apa")

    assert state["final_output"]
    assert "## References" in state["final_output"]
    assert state["trace"]
    get_settings.cache_clear()
