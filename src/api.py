"""FastAPI REST & Server-Sent Events (SSE) server for the Deep Research Agent.

Exposes clean endpoints for Next.js and external clients:
- POST /api/research: Initialize or trigger research.
- GET /api/research/{session_id}/stream: Real-time SSE event stream for live progress.
- GET /api/research/{session_id}: Retrieve full research result dossier.
- GET /api/research/history: List recent research sessions.
- DELETE /api/research/{session_id}: Delete a research session.
- GET /api/research/{session_id}/papers: Retrieve paper citations and sources.
- GET /api/memory/recall: Semantic vector memory retrieval.
- GET /api/health: LLM & environment connectivity checks.
"""

from __future__ import annotations

import asyncio
import json
import queue
import re
import threading
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agent.demo import DemoLLM
from src.agent.graph import ResearchAgent, new_session_id
from src.agent.state import make_event
from src.cli.main import _session_to_findings
from src.config import Settings, get_settings
from src.logging_utils import get_logger
from src.memory.embeddings import HashingEmbeddings
from src.memory.sqlite_store import SQLiteStore
from src.tools.formatter import format_output

logger = get_logger("src.api")

app = FastAPI(
    title="MCP Deep Research Agent API",
    description="FastAPI Backend for Next.js Stitch Deep Research UI",
    version="1.0.0",
)

# Enable CORS for Next.js frontend (default http://localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_sqlite_store: Optional[SQLiteStore] = None


def get_db_store() -> SQLiteStore:
    global _sqlite_store
    if _sqlite_store is None:
        settings = get_settings()
        _sqlite_store = SQLiteStore(settings.db_path)
        _sqlite_store.initialize()
    return _sqlite_store


def get_agent(demo: bool = False) -> ResearchAgent:
    settings = get_settings()
    if demo:
        return ResearchAgent.from_settings(settings, llm=DemoLLM(), embeddings=HashingEmbeddings())
    return ResearchAgent.from_settings(settings)


# --- Request/Response Models -----------------------------------------
class ResearchRequest(BaseModel):
    query: str = Field(..., description="Research question or topic")
    output_format: str = Field("brief", description="brief | comparison | report")
    citation_style: str = Field("apa", description="apa | mla")
    demo: bool = Field(False, description="Run in demo mode with synthetic LLM")
    force_refresh: bool = Field(False, description="Bypass cache and force rerun")


class ResearchInitResponse(BaseModel):
    session_id: str
    query: str
    output_format: str
    citation_style: str
    status: str
    stream_url: str


# --- Endpoints -------------------------------------------------------
@app.get("/api/health")
def health_check(demo: bool = False) -> Dict[str, Any]:
    """Check connectivity to LLM provider (Ollama / Cloud) and SQLite store."""
    settings = get_settings()
    try:
        agent = get_agent(demo)
        ok, msg = agent.deps.llm.ping()
    except Exception as exc:
        ok, msg = False, str(exc)

    return {
        "status": "healthy" if ok else "degraded",
        "llm_reachable": ok,
        "llm_message": msg,
        "chat_model": "synthetic-demo" if demo else settings.chat_model,
        "provider": "demo" if demo else settings.llm_provider,
        "db_path": str(settings.db_path),
    }


@app.post("/api/research", response_model=ResearchInitResponse)
def start_research(req: ResearchRequest) -> ResearchInitResponse:
    """Initialize a research task and generate a session_id."""
    clean_q = req.query.strip()
    if not clean_q:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    session_id = new_session_id()
    store = get_db_store()
    try:
        store.create_session(session_id, clean_q, req.output_format)
    except Exception as exc:
        logger.warning(f"Session creation notice: {exc}")

    return ResearchInitResponse(
        session_id=session_id,
        query=clean_q,
        output_format=req.output_format,
        citation_style=req.citation_style,
        status="initialized",
        stream_url=f"/api/research/{session_id}/stream?query={clean_q}&format={req.output_format}&style={req.citation_style}&demo={req.demo}&force_refresh={req.force_refresh}",
    )


@app.get("/api/research/{session_id}/stream")
async def stream_research(
    session_id: str,
    query: Optional[str] = None,
    output_format: str = "brief",
    citation_style: str = "apa",
    demo: bool = False,
    force_refresh: bool = False,
) -> StreamingResponse:
    """Server-Sent Events endpoint streaming real-time LangGraph execution snapshots and token-by-token text."""
    store = get_db_store()
    existing = store.get_session(session_id)
    target_query = query or (existing["user_query"] if existing else "")

    if not target_query:
        raise HTTPException(status_code=400, detail="No query associated with session")

    async def event_generator() -> AsyncIterator[str]:
        event_q: queue.Queue = queue.Queue()
        stop_signal = object()

        def background_runner() -> None:
            try:
                agent = get_agent(demo)
                for snapshot in agent.stream(
                    query=target_query,
                    output_format=output_format,
                    citation_style=citation_style,
                    session_id=session_id,
                ):
                    event_q.put({"type": "snapshot", "data": snapshot})
                event_q.put({"type": "done"})
            except Exception as exc:
                logger.error(f"Error during stream execution: {exc}")
                event_q.put({"type": "error", "error": str(exc)})
            finally:
                event_q.put(stop_signal)

        worker = threading.Thread(target=background_runner, daemon=True)
        worker.start()

        step_counter = 0
        while True:
            await asyncio.sleep(0.04)
            try:
                item = event_q.get_nowait()
            except queue.Empty:
                continue

            if item is stop_signal:
                break

            msg_type = item.get("type")
            if msg_type == "token":
                token_val = item.get("token", "")
                if token_val:
                    yield f"event: token\ndata: {json.dumps({'session_id': session_id, 'token': token_val})}\n\n"

            elif msg_type == "snapshot":
                snap = item["data"]
                step_counter += 1

                # Collect verified papers and sources from findings and research
                papers_stream: List[Dict[str, Any]] = []
                seen_stream_urls = set()
                for f in snap.get("findings", []):
                    for p in f.get("papers", []):
                        u = p.get("url") or p.get("pdf_url")
                        if u and u not in seen_stream_urls:
                            seen_stream_urls.add(u)
                            papers_stream.append({
                                "title": p.get("title") or "Academic Paper",
                                "author": p.get("author") or "Unknown Author",
                                "publisher": p.get("venue") or p.get("publisher") or "Academic Literature",
                                "url": u,
                                "formatted_apa": p.get("summary") or p.get("abstract") or "",
                                "publication_status": p.get("publication_status"),
                                "is_peer_reviewed": p.get("is_peer_reviewed", True),
                                "sub_question": f.get("sub_question"),
                            })
                    for s in f.get("sources", []):
                        u = s.get("url")
                        if u and u not in seen_stream_urls:
                            seen_stream_urls.add(u)
                            papers_stream.append({
                                "title": s.get("title") or "Verified Source",
                                "author": s.get("author") or "Unknown Author",
                                "publisher": s.get("venue") or s.get("publisher") or "Web / OpenAlex",
                                "url": u,
                                "formatted_apa": s.get("snippet") or s.get("text", "")[:200],
                                "sub_question": f.get("sub_question"),
                            })

                for r in snap.get("research", []):
                    for s in r.get("sources", []):
                        u = s.get("url")
                        if u and u not in seen_stream_urls:
                            seen_stream_urls.add(u)
                            papers_stream.append({
                                "title": s.get("title") or "Verified Source",
                                "author": s.get("author") or "Unknown Author",
                                "publisher": s.get("venue") or s.get("publisher") or "Web / OpenAlex",
                                "url": u,
                                "formatted_apa": s.get("snippet") or s.get("text", "")[:200],
                                "sub_question": r.get("sub_question"),
                            })

                has_final = bool(snap.get("final_output"))
                final_out = snap.get("final_output")

                payload = {
                    "session_id": session_id,
                    "query": target_query,
                    "step": step_counter,
                    "trace": snap.get("trace", []),
                    "sub_questions": snap.get("sub_questions", []),
                    "warnings": snap.get("warnings", []),
                    "has_final": has_final,
                    "final_output": None if has_final else None,
                    "findings": snap.get("findings", []),
                    "papers": papers_stream,
                    "metrics": snap.get("metrics", {}),
                }
                yield f"event: progress\ndata: {json.dumps(payload)}\n\n"

                # If final output is generated, stream the answer token by token over SSE
                if has_final and final_out:
                    tokens = re.findall(r"\S+|\s+", final_out)
                    accum = ""
                    for tok in tokens:
                        accum += tok
                        token_payload = {
                            "session_id": session_id,
                            "token": tok,
                            "accumulated": accum,
                        }
                        yield f"event: token\ndata: {json.dumps(token_payload)}\n\n"
                        await asyncio.sleep(0.008)

                    # Send final completion payload with complete report
                    payload["final_output"] = final_out
                    yield f"event: progress\ndata: {json.dumps(payload)}\n\n"

            elif msg_type == "done":
                yield f"event: complete\ndata: {json.dumps({'session_id': session_id, 'status': 'completed'})}\n\n"
                break

            elif msg_type == "error":
                yield f"event: error\ndata: {json.dumps({'session_id': session_id, 'error': item.get('error', 'Unknown error')})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/research/history")
def list_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve list of saved past research sessions."""
    store = get_db_store()
    return store.list_sessions(limit=limit)


@app.get("/api/research/{session_id}")
def get_session(session_id: str, style: str = "apa") -> Dict[str, Any]:
    """Retrieve a previously executed research session with rendered dossier."""
    store = get_db_store()
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Primary: use the full findings_json saved by the formatter node
    final_output = session.get("final_output")
    findings_json_str = session.get("findings_json")

    findings: List[Dict[str, Any]] = []
    if findings_json_str:
        try:
            findings = json.loads(findings_json_str)
        except (json.JSONDecodeError, TypeError):
            findings = _session_to_findings(session, style)
    else:
        findings = _session_to_findings(session, style)

    if not final_output and findings:
        final_output = format_output(
            findings,
            format=session.get("output_format", "brief"),
            query=session.get("user_query", "Research Brief"),
        )

    return {
        "session_id": session["session_id"],
        "query": session["user_query"],
        "output_format": session["output_format"],
        "created_at": session["created_at"],
        "final_output": final_output,
        "findings": findings,
    }


@app.delete("/api/research/{session_id}")
def delete_session(session_id: str) -> Dict[str, Any]:
    """Delete a research session from SQLite."""
    store = get_db_store()
    ok = store.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "deleted": True}


@app.get("/api/research/{session_id}/papers")
def get_session_papers(session_id: str) -> List[Dict[str, Any]]:
    """Retrieve all paper citations associated with a session."""
    store = get_db_store()
    papers = store.get_session_papers(session_id)
    return papers


@app.get("/api/memory/recall")
def memory_recall(
    query: str = Query(..., description="Query for semantic recall"),
    top_k: int = 5,
    demo: bool = False,
) -> List[Dict[str, Any]]:
    """Query semantic ChromaDB vector memory for past research insights."""
    agent = get_agent(demo)
    return agent.deps.tools.recall_memory("all", query, top_k=top_k)
