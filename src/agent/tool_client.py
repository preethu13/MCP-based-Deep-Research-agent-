"""In-process tool client mirroring the MCP tool surface.

The LangGraph agent calls tools through this client.  It invokes the exact same
pure tool functions the FastMCP server exposes (``src/tools/*``), wiring in the
injected memory stores and embedding provider.  This keeps the agent robust and
synchronous while ``src/mcp_server.py`` exposes the identical tools over the MCP
transport for external clients (an in-memory MCP round-trip is proven in
``tests/integration/test_mcp_server.py``).
"""

from __future__ import annotations

from typing import Any

from src.config import Settings, get_settings
from src.memory.embeddings import EmbeddingProvider, OllamaEmbeddings
from src.memory.sqlite_store import SQLiteStore
from src.memory.vector_store import VectorStore
from src.tools.citation import generate_citation as _generate_citation
from src.tools.formatter import format_output as _format_output
from src.tools.memory import recall_memory as _recall_memory
from src.tools.memory import store_memory as _store_memory
from src.tools.scrape import scrape_page as _scrape_page
from src.tools.search import search_academic_papers as _search_academic_papers
from src.tools.search import web_search as _web_search


class ToolClient:
    """Direct, synchronous access to the research tools."""

    def __init__(
        self,
        embeddings: EmbeddingProvider,
        sqlite_store: SQLiteStore,
        vector_store: VectorStore,
        settings: Settings | None = None,
    ):
        self.embeddings = embeddings
        self.sqlite = sqlite_store
        self.vector = vector_store
        self.settings = settings or get_settings()

    @classmethod
    def from_settings(
        cls, settings: Settings | None = None, embeddings: EmbeddingProvider | None = None
    ) -> ToolClient:
        settings = settings or get_settings()
        sqlite = SQLiteStore(settings.db_path)
        sqlite.initialize()
        vector = VectorStore(settings.chroma_dir)
        if embeddings is not None:
            emb = embeddings
        elif settings.llm_provider == "openai" or bool(settings.openai_api_key):
            from src.agent.api_llm import OpenAIEmbeddings

            emb = OpenAIEmbeddings(
                api_key=settings.openai_api_key,
                model=settings.openai_embed_model,
                base_url=settings.openai_base_url,
            )
        else:
            emb = OllamaEmbeddings(settings.embed_model, settings.ollama_host)
        return cls(emb, sqlite, vector, settings)

    # -- web -----------------------------------------------------------
    def search_academic_papers(self, query: str, max_results: int | None = None) -> list[dict[str, Any]]:
        return _search_academic_papers(
            query,
            max_results or self.settings.max_results_per_query,
            self.settings.search_timeout,
        )

    def web_search(self, query: str, max_results: int | None = None) -> list[dict[str, Any]]:
        return _web_search(
            query,
            max_results or self.settings.max_results_per_query,
            self.settings.search_timeout,
            include_papers=True,
        )

    def scrape_page(self, url: str) -> dict[str, Any]:
        return _scrape_page(
            url,
            timeout=self.settings.scrape_timeout,
            user_agent=self.settings.user_agent,
            respect_robots=self.settings.respect_robots_txt,
        )

    # -- citation / format --------------------------------------------
    def generate_citation(self, source: dict[str, Any], style: str = "apa") -> str:
        return _generate_citation(source, style)  # type: ignore[arg-type]

    def format_output(self, findings: list[dict[str, Any]], fmt: str, query: str = "") -> str:
        return _format_output(findings, fmt, query=query)  # type: ignore[arg-type]

    # -- memory --------------------------------------------------------
    def store_memory(
        self, session_id: str, content: str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        return _store_memory(
            session_id,
            content,
            metadata,
            vector_store=self.vector,
            sqlite_store=self.sqlite,
            embeddings=self.embeddings,
        )

    def recall_memory(
        self, session_id: str, query: str, top_k: int = 5, threshold: float | None = None
    ) -> list[dict[str, Any]]:
        return _recall_memory(
            session_id,
            query,
            top_k=top_k,
            vector_store=self.vector,
            embeddings=self.embeddings,
            threshold=self.settings.memory_relevance_threshold if threshold is None else threshold,
        )
