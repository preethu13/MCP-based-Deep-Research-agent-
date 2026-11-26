"""Central configuration, loaded from environment / ``.env``.

Core modules (stores, tools) accept explicit paths and values so they stay
unit-testable without touching global state.  Application entry points
(MCP server, CLI, UI) call :func:`get_settings` for the resolved defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load a local .env if present. Never fails if the file is absent.
load_dotenv()


def _get_str(key: str, default: str) -> str:
    value = os.getenv(key)
    return value if value not in (None, "") else default


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _get_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _get_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Resolved runtime configuration."""

    # Ollama
    ollama_host: str = "http://localhost:11434"
    chat_model: str = "llama3.1:8b"
    embed_model: str = "nomic-embed-text"
    llm_temperature: float = 0.2

    # API Keys / Cloud LLM (OpenAI, Groq, DeepSeek, OpenRouter)
    llm_provider: str = "ollama"  # "ollama" or "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_embed_model: str = "text-embedding-3-small"

    # Storage
    db_path: Path = Path("data/research.db")
    chroma_dir: Path = Path("data/chroma")
    log_file: Path = Path("data/agent.log")

    # Research behaviour
    max_results_per_query: int = 8
    sources_to_scrape: int = 5
    memory_relevance_threshold: float = 0.75
    recall_shortcircuit_hits: int = 2

    # Timeouts (seconds)
    search_timeout: int = 8
    scrape_timeout: int = 8

    # Scraping etiquette
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
    respect_robots_txt: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build (and cache) a :class:`Settings` instance from the environment."""
    return Settings(
        ollama_host=_get_str("OLLAMA_HOST", "http://localhost:11434"),
        chat_model=_get_str("OLLAMA_CHAT_MODEL", "llama3.1:8b"),
        embed_model=_get_str("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        llm_temperature=_get_float("LLM_TEMPERATURE", 0.2),
        llm_provider=_get_str("LLM_PROVIDER", "openai" if os.getenv("OPENAI_API_KEY") else "ollama"),
        openai_api_key=_get_str("OPENAI_API_KEY", ""),
        openai_model=_get_str("OPENAI_MODEL", "gpt-4o-mini"),
        openai_base_url=_get_str("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_embed_model=_get_str("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
        db_path=Path(_get_str("RESEARCH_DB_PATH", "data/research.db")),
        chroma_dir=Path(_get_str("CHROMA_DIR", "data/chroma")),
        log_file=Path(_get_str("LOG_FILE", "data/agent.log")),
        max_results_per_query=_get_int("MAX_RESULTS_PER_QUERY", 8),
        sources_to_scrape=_get_int("SOURCES_TO_SCRAPE", 5),
        memory_relevance_threshold=_get_float("MEMORY_RELEVANCE_THRESHOLD", 0.75),
        recall_shortcircuit_hits=_get_int("RECALL_SHORTCIRCUIT_HITS", 2),
        search_timeout=_get_int("SEARCH_TIMEOUT", 8),
        scrape_timeout=_get_int("SCRAPE_TIMEOUT", 8),
        user_agent=_get_str(
            "USER_AGENT",
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        ),
        respect_robots_txt=_get_bool("RESPECT_ROBOTS_TXT", True),
    )
