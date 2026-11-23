"""Typer + Rich command-line interface (F-06).

Commands
--------
    research ask "..."                 run a research query
    research sessions list             list past sessions
    research sessions recall <id>      semantic recall within/across sessions
    research sessions delete <id>      delete a session
    research export --output f.md      export a session to Markdown
    research doctor                    check the local environment
    research serve                     run the MCP tool server
    research ui                        launch the Streamlit web UI
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from src.agent.graph import ResearchAgent
from src.config import get_settings
from src.memory.sqlite_store import SQLiteStore
from src.tools.formatter import format_output

app = typer.Typer(
    add_completion=False,
    help="MCP-Powered Deep Research Agent — a $0-cost local research analyst.",
    rich_markup_mode="rich",
)
sessions_app = typer.Typer(help="Manage past research sessions.")
app.add_typer(sessions_app, name="sessions")

console = Console()
_STATUS_ICON = {"ok": "[green]●[/green]", "warn": "[yellow]▲[/yellow]", "error": "[red]✕[/red]"}
_LAST_SESSION_FILE = Path("data/.last_session")


def _store() -> SQLiteStore:
    store = SQLiteStore(get_settings().db_path)
    store.initialize()
    return store


def _build_agent(settings, demo: bool = False) -> ResearchAgent:
    if demo:
        from src.agent.demo import DemoLLM
        from src.memory.embeddings import HashingEmbeddings

        return ResearchAgent.from_settings(settings, llm=DemoLLM(), embeddings=HashingEmbeddings())
    return ResearchAgent.from_settings(settings)


def _render_trace(trace: list[dict]) -> Panel:
    table = Table.grid(padding=(0, 1))
    table.add_column(justify="right", style="dim", width=3)
    table.add_column(width=2)
    table.add_column()
    for event in trace[-14:]:
        icon = _STATUS_ICON.get(event["status"], "○")
        detail = f"  [dim]{event['detail']}[/dim]" if event.get("detail") else ""
        table.add_row(str(event["step"]), icon, f"[bold]{event['title']}[/bold]{detail}")
    return Panel(table, title="[#E8B15A]research log[/#E8B15A]", border_style="yellow")


def _remember_session(session_id: str) -> None:
    try:
        _LAST_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LAST_SESSION_FILE.write_text(session_id, encoding="utf-8")
    except Exception:
        pass


def _session_to_findings(session: dict, style: str) -> list[dict]:
    findings = []
    for finding in session.get("findings", []):
        citations, sources = [], []
        for citation in finding.get("citations", []):
            formatted = citation.get("formatted_mla" if style == "mla" else "formatted_apa")
            if formatted:
                citations.append(formatted)
            sources.append({"url": citation["url"], "title": citation.get("title")})
        findings.append(
            {
                "sub_question": finding.get("sub_question"),
                "claim": finding.get("claim", ""),
                "citations": citations,
                "sources": sources,
            }
        )
    return findings


# ─────────────────────────────────────────────────────────────
# ask
# ─────────────────────────────────────────────────────────────
@app.command()
def ask(
    query: str = typer.Argument(..., help="Your research question."),
    format: str = typer.Option("brief", "--format", "-f", help="brief | comparison | report"),
    style: str = typer.Option("apa", "--style", "-s", help="Citation style: apa | mla"),
    session: Optional[str] = typer.Option(None, help="Reuse/resume a specific session id."),
    demo: bool = typer.Option(False, "--demo", help="Run offline with a synthetic model (no Ollama)."),
) -> None:
    """Run a multi-step research query and print a cited report."""
    settings = get_settings()
    agent = _build_agent(settings, demo=demo)

    ok, message = agent.deps.llm.ping()
    if not ok:
        console.print(
            Panel(
                f"[bold red]Ollama is not reachable[/bold red] at {settings.ollama_host}\n\n"
                f"[dim]{message}[/dim]\n\n"
                "Start it and pull the models:\n"
                "  [bold]ollama serve[/bold]\n"
                f"  [bold]ollama pull {settings.chat_model}[/bold]\n"
                f"  [bold]ollama pull {settings.embed_model}[/bold]",
                title="Setup required",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    console.print(Panel(f"[bold]{query}[/bold]", title="Deep Research", border_style="yellow"))

    final_state: dict = {}
    with Live(_render_trace([]), console=console, refresh_per_second=8) as live:
        for state in agent.stream(query, format, style, session_id=session):
            final_state = state
            live.update(_render_trace(state.get("trace", [])))

    _remember_session(final_state.get("session_id", ""))
    console.print()
    console.print(Markdown(final_state.get("final_output", "_No output produced._")))
    console.print(f"\n[dim]session: {final_state.get('session_id', '?')}[/dim]")


# ─────────────────────────────────────────────────────────────
# sessions
# ─────────────────────────────────────────────────────────────
@sessions_app.command("list")
def sessions_list(limit: int = typer.Option(20, help="Max sessions to show.")) -> None:
    """List past research sessions, most recent first."""
    rows = _store().list_sessions(limit=limit)
    if not rows:
        console.print("[dim]No sessions yet. Run:  research ask \"your question\"[/dim]")
        return
    table = Table(title="Research sessions", border_style="yellow", header_style="bold")
    table.add_column("Session", style="cyan", no_wrap=True)
    table.add_column("Query")
    table.add_column("Format")
    table.add_column("Findings", justify="right")
    table.add_column("Status")
    table.add_column("Created", style="dim")
    for row in rows:
        table.add_row(
            row["session_id"],
            (row["user_query"][:60] + "…") if len(row["user_query"]) > 60 else row["user_query"],
            row["output_format"] or "—",
            str(row["finding_count"]),
            row["status"],
            str(row["created_at"]),
        )
    console.print(table)


@sessions_app.command("recall")
def sessions_recall(
    session_id: str = typer.Argument("all", help="Session id, or 'all' for global recall."),
    query: str = typer.Option(..., "--query", "-q", help="What to search your memory for."),
    top_k: int = typer.Option(5, help="How many memories to return."),
) -> None:
    """Semantically recall past findings."""
    agent = ResearchAgent.from_settings()
    hits = agent.deps.tools.recall_memory(session_id, query, top_k=top_k, threshold=0.0)
    if not hits:
        console.print("[dim]No relevant memories found.[/dim]")
        return
    for hit in hits:
        console.print(
            Panel(
                hit["content"],
                title=f"similarity {hit['similarity_score']:.2f} · {hit['session_id']}",
                border_style="yellow",
            )
        )


@sessions_app.command("delete")
def sessions_delete(session_id: str = typer.Argument(..., help="Session id to delete.")) -> None:
    """Delete a session and its findings, citations and memory pointers."""
    deleted = _store().delete_session(session_id)
    if deleted:
        console.print(f"[green]Deleted[/green] {session_id}")
    else:
        console.print(f"[yellow]No such session:[/yellow] {session_id}")


# ─────────────────────────────────────────────────────────────
# export
# ─────────────────────────────────────────────────────────────
@app.command()
def export(
    output: Path = typer.Option(Path("findings.md"), "--output", "-o", help="Output file path."),
    style: str = typer.Option("apa", "--format", "-f", help="Citation style: apa | mla"),
    session: Optional[str] = typer.Option(None, help="Session id (defaults to the last one)."),
) -> None:
    """Export a session's findings to a Markdown file."""
    store = _store()
    session_id = session
    if session_id is None and _LAST_SESSION_FILE.exists():
        session_id = _LAST_SESSION_FILE.read_text(encoding="utf-8").strip()
    if session_id is None:
        rows = store.list_sessions(limit=1)
        session_id = rows[0]["session_id"] if rows else None
    if session_id is None:
        console.print("[yellow]No sessions to export.[/yellow]")
        raise typer.Exit(code=1)

    session_data = store.get_session(session_id)
    if session_data is None:
        console.print(f"[yellow]No such session:[/yellow] {session_id}")
        raise typer.Exit(code=1)

    findings = _session_to_findings(session_data, style)
    rendered = format_output(
        findings, session_data.get("output_format", "brief"), query=session_data["user_query"]
    )
    output.write_text(rendered, encoding="utf-8")
    console.print(f"[green]Exported[/green] {session_id} → {output} ({style.upper()})")


# ─────────────────────────────────────────────────────────────
# doctor / serve / ui
# ─────────────────────────────────────────────────────────────
@app.command()
def doctor() -> None:
    """Check that the local environment is ready."""
    settings = get_settings()
    table = Table(title="Environment check", border_style="yellow")
    table.add_column("Component")
    table.add_column("Status")

    agent = ResearchAgent.from_settings(settings)
    ok, message = agent.deps.llm.ping()
    provider_name = "Cloud API (OpenAI-compatible)" if (settings.llm_provider == "openai" or settings.openai_api_key) else "Ollama (local)"
    model_name = settings.openai_model if (settings.llm_provider == "openai" or settings.openai_api_key) else settings.chat_model
    embed_name = settings.openai_embed_model if (settings.llm_provider == "openai" or settings.openai_api_key) else settings.embed_model

    table.add_row("LLM Provider", provider_name)
    table.add_row("LLM Status", "[green]reachable[/green]" if ok else f"[red]unreachable[/red] ({message})")
    table.add_row("Chat model", model_name)
    table.add_row("Embedding model", embed_name)
    table.add_row("SQLite", str(settings.db_path))
    table.add_row("ChromaDB", str(settings.chroma_dir))
    console.print(table)
    if not ok and provider_name.startswith("Ollama"):
        console.print("[dim]Start Ollama with:  ollama serve[/dim]")


@app.command()
def serve() -> None:
    """Run the FastMCP tool server (stdio transport)."""
    from src.mcp_server import main as serve_main

    serve_main()


@app.command()
def ui() -> None:
    """Launch the Streamlit web UI."""
    app_path = Path(__file__).resolve().parents[1] / "ui" / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=False)


if __name__ == "__main__":
    app()
