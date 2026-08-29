"""Tests for environment-driven configuration parsing."""

from __future__ import annotations

from pathlib import Path

from src.config import Settings, get_settings


def test_defaults():
    s = Settings()
    assert s.chat_model == "llama3.1:8b"
    assert s.embed_model == "nomic-embed-text"
    assert s.respect_robots_txt is True
    assert s.db_path == Path("data/research.db")


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("OLLAMA_CHAT_MODEL", "mistral")
    monkeypatch.setenv("MAX_RESULTS_PER_QUERY", "9")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.7")
    monkeypatch.setenv("RESPECT_ROBOTS_TXT", "false")
    get_settings.cache_clear()
    s = get_settings()
    assert s.chat_model == "mistral"
    assert s.max_results_per_query == 9
    assert s.llm_temperature == 0.7
    assert s.respect_robots_txt is False
    get_settings.cache_clear()


def test_invalid_numbers_fall_back_to_defaults(monkeypatch):
    monkeypatch.setenv("MAX_RESULTS_PER_QUERY", "not-a-number")
    monkeypatch.setenv("LLM_TEMPERATURE", "")
    get_settings.cache_clear()
    s = get_settings()
    assert s.max_results_per_query == 5
    assert s.llm_temperature == 0.2
    get_settings.cache_clear()


def test_bool_parsing_variants(monkeypatch):
    for raw, expected in [("1", True), ("yes", True), ("ON", True), ("0", False), ("no", False)]:
        monkeypatch.setenv("RESPECT_ROBOTS_TXT", raw)
        get_settings.cache_clear()
        assert get_settings().respect_robots_txt is expected
    get_settings.cache_clear()
