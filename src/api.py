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


# --- Global singletons & helpers -------------------------------------
_active_tasks: Dict[str, queue.Queue] = {}
_store: Optional[SQLiteStore] = None


def get_db_store() -> SQLiteStore:
    global _store
    if _store is None:
        _store = SQLiteStore(get_settings().db_path)
        _store.initialize()
    return _store


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
    """Server-Sent Events endpoint streaming real-time LangGraph execution snapshots."""
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
                    force_refresh=force_refresh,
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
def get_session_details(session_id: str, style: str = "apa") -> Dict[str, Any]:
    """Retrieve full details of a specific session including formatted markdown & findings."""
    store = get_db_store()
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    findings = _session_to_findings(session, style)
    final_output = session.get("final_output")
    if not final_output and session.get("user_query"):
        final_output = format_output(
            findings, session.get("output_format", "brief"), query=session["user_query"]
        )

    return {
        "session_id": session_id,
        "query": session.get("user_query"),
        "created_at": session.get("created_at"),
        "output_format": session.get("output_format", "brief"),
        "status": session.get("status", "completed"),
        "final_output": final_output,
        "findings": session.get("findings", []),
        "processed_findings": findings,
    }


@app.delete("/api/research/{session_id}")
def delete_session(session_id: str) -> Dict[str, Any]:
    """Delete a research session from SQLite."""
    store = get_db_store()
    success = store.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or already deleted")
    return {"session_id": session_id, "deleted": True}


@app.get("/api/research/{session_id}/papers")
def get_session_papers(session_id: str) -> List[Dict[str, Any]]:
    """Retrieve papers and citations discovered in this session."""
    store = get_db_store()
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    papers: List[Dict[str, Any]] = []
    seen_urls = set()

    # 1. First, check findings_json in the session record
    findings_json = session.get("findings_json")
    parsed_findings = []
    if findings_json:
        try:
            parsed_findings = json.loads(findings_json)
        except Exception:
            pass

    for f in parsed_findings:
        # Check explicit papers
        for p in f.get("papers", []):
            u = p.get("url") or p.get("pdf_url")
            if u and u not in seen_urls:
                seen_urls.add(u)
                papers.append({
                    "title": p.get("title") or "Academic Paper",
                    "author": p.get("author") or "Unknown Author",
                    "publisher": p.get("venue") or p.get("publisher") or "Academic Literature",
                    "url": u,
                    "formatted_apa": p.get("summary") or p.get("abstract") or "",
                    "publication_status": p.get("publication_status"),
                    "is_peer_reviewed": p.get("is_peer_reviewed", True),
                    "sub_question": f.get("sub_question"),
                })

        # Check sources
        for s in f.get("sources", []):
            u = s.get("url")
            if u and u not in seen_urls:
                seen_urls.add(u)
                papers.append({
                    "title": s.get("title") or "Verified Source",
                    "author": s.get("author") or "Unknown Author",
                    "publisher": s.get("venue") or s.get("publisher") or "Web / OpenAlex",
                    "url": u,
                    "formatted_apa": s.get("snippet") or s.get("text", "")[:200],
                    "sub_question": f.get("sub_question"),
                })

    # 2. Check relational findings and citations table
    for f in session.get("findings", []):
        for c in f.get("citations", []):
            url = c.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                papers.append({
                    "citation_id": c.get("citation_id"),
                    "title": c.get("title") or "Academic Citation",
                    "author": c.get("author") or "Unknown Author",
                    "publisher": c.get("publisher") or "OpenAlex / DuckDuckGo",
                    "url": url,
                    "formatted_apa": c.get("formatted_apa"),
                    "formatted_mla": c.get("formatted_mla"),
                    "sub_question": f.get("sub_question"),
                })

    # 3. Fallback: Parse URLs and references from final_output if still empty
    final_output = session.get("final_output", "")
    if not papers and final_output:
        import re
        matches = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', final_output)
        for title, url in matches:
            if url not in seen_urls and not url.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                seen_urls.add(url)
                papers.append({
                    "title": title,
                    "author": "Cited in dossier",
                    "publisher": "Academic / Web Source",
                    "url": url,
                    "formatted_apa": f"Retrieved from {url}",
                })

    return papers


@app.get("/api/memory/recall")
def recall_memory(
    query: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
    demo: bool = False,
) -> List[Dict[str, Any]]:
    """Semantic vector memory search across previous findings."""
    agent = get_agent(demo)
    try:
        hits = agent.deps.tools.recall_memory("all", query.strip(), top_k=top_k, threshold=0.0)
        return hits
    except Exception as exc:
        logger.error(f"Memory recall error: {exc}")
        return []
