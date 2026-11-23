"""The Night Desk — Streamlit web interface for the Deep Research Agent (F-07).

A deep-ink research workspace with a live "research log" that traces every tool
call the agent makes.  Runs against Ollama in live mode, or fully offline with a
synthetic model via the Demo-mode toggle (no Ollama, no network beyond search).

Launch with::

    research ui           # or: streamlit run src/ui/app.py
"""

from __future__ import annotations

import html
import sys
from datetime import date
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path when running via `streamlit run src/ui/app.py`
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from src.agent.graph import ResearchAgent
from src.cli.main import _session_to_findings
from src.config import get_settings
from src.memory.sqlite_store import SQLiteStore
from src.tools.formatter import format_output

_ASSETS = Path(__file__).resolve().parent / "assets" / "styles.css"
_FORMATS = {"Brief": "brief", "Comparison": "comparison", "Report": "report"}
_STYLES = {"APA 7th": "apa", "MLA 9th": "mla"}


# ─────────────────────────────────────────────────────────────────────
# resources (cached across reruns)
# ─────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_agent(demo: bool) -> ResearchAgent:
    settings = get_settings()
    if demo:
        from src.agent.demo import DemoLLM
        from src.memory.embeddings import HashingEmbeddings

        return ResearchAgent.from_settings(settings, llm=DemoLLM(), embeddings=HashingEmbeddings())
    return ResearchAgent.from_settings(settings)


@st.cache_resource(show_spinner=False)
def get_store() -> SQLiteStore:
    store = SQLiteStore(get_settings().db_path)
    store.initialize()
    return store


@st.cache_data(ttl=20, show_spinner=False)
def check_env(demo: bool) -> tuple[bool, str]:
    try:
        return get_agent(demo).deps.llm.ping()
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)


def load_css() -> None:
    try:
        st.markdown(f"<style>{_ASSETS.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    except OSError:
        pass


# ─────────────────────────────────────────────────────────────────────
# rendering helpers
# ─────────────────────────────────────────────────────────────────────
_STATUS_CLASS = {"ok": "status-ok", "warn": "status-warn", "error": "status-error"}


def render_log(trace: list[dict[str, Any]], *, live: bool = False) -> str:
    label = "Research log · live" if live else "Research log"
    if not trace:
        return (
            f'<div class="panel"><div class="panel-label">{label}</div>'
            '<div style="color:var(--muted)">The desk is quiet. Ask a question to begin.</div></div>'
        )
    rows = []
    for event in trace:
        cls = _STATUS_CLASS.get(event.get("status", "ok"), "status-ok")
        tool = event.get("tool") or event.get("node") or ""
        step = str(event.get("step", "")).zfill(2)
        title = html.escape(str(event.get("title", "")))
        detail = html.escape(str(event.get("detail", "") or ""))
        tool_html = f'<span class="log-tool">{html.escape(tool)}</span>' if tool else ""
        detail_html = f'<div class="log-detail">{detail}</div>' if detail else ""
        rows.append(
            f'<div class="log-entry {cls}">'
            '<div class="log-rail"><span class="log-dot"></span></div>'
            '<div class="log-body">'
            f'<div class="log-head">{tool_html}<span class="log-step">#{step}</span></div>'
            f'<div class="log-title">{title}</div>{detail_html}'
            "</div></div>"
        )
    return (
        f'<div class="panel"><div class="panel-label">{label}</div>'
        f'<div class="log">{"".join(rows)}</div></div>'
    )


def render_report(result: dict[str, Any]) -> None:
    md = result.get("final_output") or "_No output produced._"
    warnings = result.get("warnings") or []
    session_id = result.get("session_id", "research")

    st.markdown('<div class="panel-label" style="margin-top:1.6rem">The Dossier</div>', unsafe_allow_html=True)
    if warnings:
        st.warning("  ·  ".join(dict.fromkeys(warnings)))
    st.markdown(md)

    left, right = st.columns([1, 2])
    with left:
        st.download_button(
            "⤓  Download Markdown",
            md,
            file_name=f"{session_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with right:
        with st.expander("View Markdown source"):
            st.code(md, language="markdown")


def session_to_markdown(store: SQLiteStore, session_id: str, style: str) -> dict[str, Any] | None:
    data = store.get_session(session_id)
    if data is None:
        return None
    findings = _session_to_findings(data, style)
    md = format_output(findings, data.get("output_format", "brief"), query=data["user_query"])
    return {"final_output": md, "session_id": session_id, "trace": [], "warnings": []}


# ─────────────────────────────────────────────────────────────────────
# app
# ─────────────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(page_title="The Night Desk · Deep Research", page_icon="🌙", layout="wide")
    load_css()

    state = st.session_state
    state.setdefault("result", None)
    state.setdefault("result_style", "apa")

    # ---- sidebar -----------------------------------------------------
    with st.sidebar:
        st.markdown('<div class="panel-label">The Night Desk</div>', unsafe_allow_html=True)
        st.markdown("A local research analyst. Nothing leaves your machine except the searches it runs.")

        st.markdown("###### Model")
        demo = st.toggle(
            "Demo mode (no Ollama)",
            value=not check_env(False)[0],
            help="Run offline with a deterministic synthetic model. No Ollama required.",
        )
        ok, message = check_env(demo)
        badge = f'<span class="badge {"on" if ok else "off"}">{"● reachable" if ok else "○ offline"}</span>'
        engine = "demo model" if demo else get_settings().chat_model
        st.markdown(f"{badge} &nbsp; <span class='badge'>{html.escape(engine)}</span>", unsafe_allow_html=True)
        if not ok and not demo:
            st.caption(f"Ollama unreachable — {message}. Toggle Demo mode to explore offline.")

        st.markdown("###### Output")
        fmt_label = st.radio("Format", list(_FORMATS), horizontal=True, label_visibility="collapsed")
        style_label = st.radio("Citations", list(_STYLES), horizontal=True, label_visibility="collapsed")

        st.divider()
        _render_memory_search(demo)
        st.divider()
        _render_history()

    # ---- main --------------------------------------------------------
    st.markdown(
        '<div class="hero">'
        '<div class="hero-eyebrow">Local · Private · $0 per query</div>'
        '<h1 class="hero-title">The Night <span class="lamp">Desk</span></h1>'
        '<p class="hero-sub">An autonomous analyst that plans a question, reads the open web, '
        "cites every claim, and remembers what you asked before — running entirely on your machine.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    with st.form("query_form"):
        query = st.text_input(
            "Research question",
            placeholder="e.g.  Compare Redis and Memcached for session caching",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Begin research  →", use_container_width=False)

    log_slot = st.empty()
    fmt, style = _FORMATS[fmt_label], _STYLES[style_label]

    if submitted and query.strip():
        _run_research(query.strip(), fmt, style, demo, log_slot)

    result = state.get("result")
    if result:
        if not (submitted and query.strip()):
            log_slot.empty()  # keep log slot clear when showing a cached result
        render_report(result)


def _run_research(query: str, fmt: str, style: str, demo: bool, log_slot: Any) -> None:
    agent = get_agent(demo)
    final: dict[str, Any] = {}
    steps = [
        "Analyzing research question...",
        "Retrieving academic papers & literature...",
        "Analyzing paper abstracts & methodology...",
        "Synthesizing cross-paper findings...",
        "Compiling research dossier...",
    ]
    step_i = 0
    try:
        with st.spinner(f"🔍 {steps[step_i]}"):
            for snapshot in agent.stream(query, fmt, style):
                final = snapshot
                # Advance the spinner label based on trace length
                n = len(snapshot.get("trace", []))
                new_i = min(n // 2, len(steps) - 1)
                if new_i != step_i:
                    step_i = new_i
    except Exception as exc:
        st.error(f"Research could not complete: {exc}")
        return
    if final:
        st.session_state.result = final
        st.session_state.result_style = style
        # Clear the log slot
        log_slot.empty()


def _render_memory_search(demo: bool) -> None:
    st.markdown('<div class="panel-label">Recall memory</div>', unsafe_allow_html=True)
    q = st.text_input("Recall", placeholder="search past findings…", label_visibility="collapsed", key="recall_q")
    if not q.strip():
        return
    try:
        hits = get_agent(demo).deps.tools.recall_memory("all", q.strip(), top_k=5, threshold=0.0)
    except Exception as exc:
        st.caption(f"Recall unavailable: {exc}")
        return
    if not hits:
        st.caption("No related memories yet.")
        return
    for hit in hits:
        score = hit.get("similarity_score", 0.0)
        content = html.escape(hit.get("content", ""))[:220]
        st.markdown(
            f'<div class="panel" style="padding:.6rem .8rem;margin-bottom:.5rem">'
            f'<span class="badge">sim {score:.2f}</span>'
            f'<div style="color:#D8D2C4;font-size:.85rem;margin-top:.4rem">{content}</div></div>',
            unsafe_allow_html=True,
        )


def _render_history() -> None:
    st.markdown('<div class="panel-label">Recent sessions</div>', unsafe_allow_html=True)
    store = get_store()
    rows = store.list_sessions(limit=8)
    if not rows:
        st.caption("No sessions yet.")
        return
    style = st.session_state.get("result_style", "apa")
    for row in rows:
        sid = row["session_id"]
        preview = row["user_query"]
        preview = (preview[:38] + "…") if len(preview) > 38 else preview
        with st.container():
            st.markdown(
                f'<div style="font-size:.86rem;color:#D8D2C4">{html.escape(preview)}</div>'
                f'<div class="log-detail">{row["output_format"] or "—"} · {row["finding_count"]} findings</div>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            if c1.button("Open", key=f"open_{sid}", use_container_width=True):
                loaded = session_to_markdown(store, sid, style)
                if loaded:
                    st.session_state.result = loaded
                    st.rerun()
            if c2.button("Delete", key=f"del_{sid}", use_container_width=True):
                store.delete_session(sid)
                if (st.session_state.get("result") or {}).get("session_id") == sid:
                    st.session_state.result = None
                st.rerun()


if __name__ == "__main__":
    main()
