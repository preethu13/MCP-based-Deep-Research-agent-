"""LangGraph orchestration (F-02, AG-*).

Wires the four nodes into the explicit state machine

    START -> planner -> researcher -> synthesizer -> formatter -> END

and exposes :class:`ResearchAgent`, the high-level entry point used by the CLI
and Streamlit UI.  Dependencies (LLM, tools, stores) are injected, so the same
graph runs against a fake LLM in tests and Ollama in production.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.agent.llm import OllamaLLM
from src.agent.nodes.formatter import formatter_node
from src.agent.nodes.planner import planner_node
from src.agent.nodes.researcher import researcher_node
from src.agent.nodes.synthesizer import synthesizer_node
from src.agent.state import AgentDeps, ResearchState, make_event
from src.agent.tool_client import ToolClient
from src.config import Settings, get_settings

_VALID_FORMATS = {"brief", "comparison", "report"}
_VALID_STYLES = {"apa", "mla"}


def build_graph(deps: AgentDeps) -> Any:
    """Compile the research state machine with dependencies bound to each node."""
    graph = StateGraph(ResearchState)
    graph.add_node("planner", partial(planner_node, deps=deps))
    graph.add_node("researcher", partial(researcher_node, deps=deps))
    graph.add_node("synthesizer", partial(synthesizer_node, deps=deps))
    graph.add_node("formatter", partial(formatter_node, deps=deps))

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "synthesizer")
    graph.add_edge("synthesizer", "formatter")
    graph.add_edge("formatter", END)
    return graph.compile()


def new_session_id() -> str:
    return f"sess_{uuid.uuid4().hex[:12]}"


class ResearchAgent:
    """High-level driver: create a session, run the graph, return final state."""

    def __init__(self, deps: AgentDeps):
        self.deps = deps
        self.graph = build_graph(deps)

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        llm: Any | None = None,
        embeddings: Any | None = None,
    ) -> ResearchAgent:
        settings = settings or get_settings()
        tools = ToolClient.from_settings(settings, embeddings=embeddings)
        if llm is None:
            if settings.llm_provider == "openai" or bool(settings.openai_api_key):
                from src.agent.api_llm import OpenAILLM

                llm = OpenAILLM(
                    api_key=settings.openai_api_key,
                    model=settings.openai_model,
                    base_url=settings.openai_base_url,
                    temperature=settings.llm_temperature,
                )
            else:
                llm = OllamaLLM(settings.chat_model, settings.ollama_host, settings.llm_temperature)
        deps = AgentDeps(llm=llm, tools=tools, sqlite=tools.sqlite, settings=settings)
        return cls(deps)

    def _initial_state(
        self, query: str, output_format: str, citation_style: str, session_id: str
    ) -> ResearchState:
        output_format = output_format if output_format in _VALID_FORMATS else "brief"
        citation_style = citation_style if citation_style in _VALID_STYLES else "apa"
        try:
            self.deps.sqlite.create_session(session_id, query, output_format)
        except Exception:
            pass
        return {
            "query": query,
            "output_format": output_format,
            "citation_style": citation_style,
            "session_id": session_id,
            "trace": [],
            "warnings": [],
        }

    def run(
        self,
        query: str,
        output_format: str = "brief",
        citation_style: str = "apa",
        session_id: str | None = None,
    ) -> ResearchState:
        session_id = session_id or new_session_id()
        state = self._initial_state(query, output_format, citation_style, session_id)
        try:
            return self.graph.invoke(state)  # type: ignore[return-value]
        except Exception:
            try:
                self.deps.sqlite.update_session_status(session_id, "failed")
            except Exception:
                pass
            raise

    def stream(
        self,
        query: str,
        output_format: str = "brief",
        citation_style: str = "apa",
        session_id: str | None = None,
    ) -> Iterator[ResearchState]:
        """Yield the accumulating state after each node (drives the live UI trace)."""
        session_id = session_id or new_session_id()
        state = self._initial_state(query, output_format, citation_style, session_id)
        for update in self.graph.stream(state, stream_mode="values"):
            yield update  # type: ignore[misc]
