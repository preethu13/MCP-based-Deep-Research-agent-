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
from src.agent.profiler import Profiler, get_profiler
from src.agent.state import AgentDeps, ResearchState, make_event
from src.agent.tool_client import ToolClient
from src.config import Settings, get_settings

_VALID_FORMATS = {"brief", "comparison", "report"}
_VALID_STYLES = {"apa", "mla"}


def build_graph(deps: AgentDeps) -> Any:
    """Compile the research state machine with dependencies bound to each node."""
    graph = StateGraph(ResearchState)

    def _run_planner(state: ResearchState) -> dict[str, Any]:
        with get_profiler().measure_node("planner"):
            return planner_node(state, deps=deps)

    def _run_researcher(state: ResearchState) -> dict[str, Any]:
        with get_profiler().measure_node("researcher"):
            return researcher_node(state, deps=deps)

    def _run_synthesizer(state: ResearchState) -> dict[str, Any]:
        with get_profiler().measure_node("synthesizer"):
            return synthesizer_node(state, deps=deps)

    def _run_formatter(state: ResearchState) -> dict[str, Any]:
        prof = get_profiler()
        with prof.measure_node("formatter"):
            out = formatter_node(state, deps=deps)
        out["metrics"] = prof.get_metrics()
        prof.log_summary()
        return out

    graph.add_node("planner", _run_planner)
    graph.add_node("researcher", _run_researcher)
    graph.add_node("synthesizer", _run_synthesizer)
    graph.add_node("formatter", _run_formatter)

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
        force_refresh: bool = False,
    ) -> ResearchState:
        Profiler.reset()
        output_format = output_format if output_format in _VALID_FORMATS else "brief"
        citation_style = citation_style if citation_style in _VALID_STYLES else "apa"

        # 1. Instant Return for Previously Researched Queries (Database Cache)
        if not force_refresh:
            cached_session = self.deps.sqlite.find_completed_session(query, output_format)
            if cached_session and cached_session.get("final_output"):
                findings = cached_session.get("findings", [])
                sub_qs = [f.get("sub_question") for f in findings if f.get("sub_question")]
                trace = [
                    make_event(
                        1,
                        "researcher",
                        "database_cache_hit",
                        "Retrieved existing completed research from database",
                        f"Reused findings, claims and bibliography from session {cached_session['session_id']}",
                        "ok",
                    )
                ]
                return {
                    "query": query,
                    "output_format": output_format,
                    "citation_style": citation_style,
                    "session_id": cached_session["session_id"],
                    "sub_questions": sub_qs,
                    "research": [],
                    "findings": findings,
                    "final_output": cached_session["final_output"],
                    "trace": trace,
                    "warnings": [f"Served from database cache (session {cached_session['session_id']})."],
                    "metrics": {
                        "total_duration_seconds": 0.05,
                        "cached": True,
                        "database_cache_hit": True,
                        "reused_session": cached_session["session_id"],
                    },
                }

        session_id = session_id or new_session_id()
        state = self._initial_state(query, output_format, citation_style, session_id)
        try:
            final_state = self.graph.invoke(state)  # type: ignore[return-value]
            # Save final output & structured findings to SQLite session for fast repeated lookups
            if final_state.get("final_output"):
                self.deps.sqlite.save_session_result(
                    session_id, final_state["final_output"], final_state.get("findings", [])
                )
            return final_state
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
        force_refresh: bool = False,
    ) -> Iterator[ResearchState]:
        """Yield the accumulating state after each node (drives the live UI trace)."""
        output_format = output_format if output_format in _VALID_FORMATS else "brief"
        citation_style = citation_style if citation_style in _VALID_STYLES else "apa"

        # Check completed cache for streaming too
        if not force_refresh:
            cached_session = self.deps.sqlite.find_completed_session(query, output_format)
            if cached_session and cached_session.get("final_output"):
                findings = cached_session.get("findings", [])
                sub_qs = [f.get("sub_question") for f in findings if f.get("sub_question")]
                trace = [
                    make_event(
                        1,
                        "researcher",
                        "database_cache_hit",
                        "Retrieved existing completed research from database",
                        f"Reused findings, claims and bibliography from session {cached_session['session_id']}",
                        "ok",
                    )
                ]
                yield {
                    "query": query,
                    "output_format": output_format,
                    "citation_style": citation_style,
                    "session_id": cached_session["session_id"],
                    "sub_questions": sub_qs,
                    "research": [],
                    "findings": findings,
                    "final_output": cached_session["final_output"],
                    "trace": trace,
                    "warnings": [f"Served from database cache (session {cached_session['session_id']})."],
                    "metrics": {
                        "total_duration_seconds": 0.05,
                        "cached": True,
                        "database_cache_hit": True,
                        "reused_session": cached_session["session_id"],
                    },
                }
                return

        session_id = session_id or new_session_id()
        state = self._initial_state(query, output_format, citation_style, session_id)
        last_state = state
        for update in self.graph.stream(state, stream_mode="values"):
            last_state = update
            yield update  # type: ignore[misc]

        if last_state.get("final_output"):
            try:
                self.deps.sqlite.save_session_result(
                    session_id, last_state["final_output"], last_state.get("findings", [])
                )
            except Exception:
                pass
