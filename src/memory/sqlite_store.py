"""SQLite structured memory store (MEM-01, MEM-04, MEM-05).

Persists sessions, findings and citations with foreign-key relations, plus a
pointer table linking rows to their ChromaDB vector IDs.  A file-backed SQLite
database means memory survives process restarts (MEM-05 / AC-04).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id      TEXT PRIMARY KEY,
    user_query      TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    output_format   TEXT CHECK(output_format IN ('brief','comparison','report')),
    status          TEXT CHECK(status IN ('running','completed','failed')) DEFAULT 'running',
    final_output    TEXT,
    findings_json   TEXT
);

CREATE TABLE IF NOT EXISTS findings (
    finding_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    sub_question    TEXT,
    claim_text      TEXT NOT NULL,
    confidence      REAL DEFAULT 1.0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS citations (
    citation_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id      INTEGER NOT NULL REFERENCES findings(finding_id) ON DELETE CASCADE,
    url             TEXT NOT NULL,
    title           TEXT,
    author          TEXT,
    publisher       TEXT,
    accessed_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    formatted_apa   TEXT,
    formatted_mla   TEXT
);

CREATE TABLE IF NOT EXISTS memories (
    memory_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    chroma_vector_id TEXT NOT NULL UNIQUE,
    summary_text     TEXT NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_findings_session ON findings(session_id);
CREATE INDEX IF NOT EXISTS idx_citations_finding ON citations(finding_id);
CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id);
"""


class SQLiteStore:
    """Thin, connection-per-operation wrapper around the research database."""

    def __init__(self, db_path: str | Path = "data/research.db"):
        self.db_path = Path(db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        """Create tables and indexes if they do not exist."""
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            # Migrate existing databases: add columns if missing
            existing_cols = {
                row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
            }
            if "final_output" not in existing_cols:
                conn.execute("ALTER TABLE sessions ADD COLUMN final_output TEXT")
            if "findings_json" not in existing_cols:
                conn.execute("ALTER TABLE sessions ADD COLUMN findings_json TEXT")

    # -- sessions -------------------------------------------------------
    def create_session(self, session_id: str, user_query: str, output_format: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, user_query, output_format) VALUES (?, ?, ?)",
                (session_id, user_query, output_format),
            )

    def update_session_status(self, session_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET status = ? WHERE session_id = ?", (status, session_id)
            )

    def save_session_result(
        self,
        session_id: str,
        final_output: str,
        findings: list[dict[str, Any]] | None = None,
    ) -> None:
        """Persist the formatted output and findings JSON so they survive page reloads."""
        import json as _json

        findings_json = _json.dumps(findings) if findings else None
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET final_output = ?, findings_json = ? WHERE session_id = ?",
                (final_output, findings_json, session_id),
            )

    def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT s.session_id, s.user_query, s.created_at, s.output_format, s.status,
                       COUNT(DISTINCT f.finding_id) AS finding_count
                FROM sessions s
                LEFT JOIN findings f ON f.session_id = s.session_id
                GROUP BY s.session_id
                ORDER BY s.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def search_sessions(self, text: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT session_id, user_query, created_at, output_format, status
                FROM sessions
                WHERE user_query LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f"%{text}%", limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Return a session with its nested findings and citations, or ``None``."""
        with self._connect() as conn:
            session = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if session is None:
                return None

            findings = conn.execute(
                "SELECT * FROM findings WHERE session_id = ? ORDER BY finding_id", (session_id,)
            ).fetchall()

            result = dict(session)
            result["findings"] = []
            for finding in findings:
                citations = conn.execute(
                    "SELECT * FROM citations WHERE finding_id = ? ORDER BY citation_id",
                    (finding["finding_id"],),
                ).fetchall()
                fdict = dict(finding)
                fdict["citations"] = [dict(c) for c in citations]
                result["findings"].append(fdict)
            return result

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and (via cascade) its findings, citations, memory pointers."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            return cur.rowcount > 0

    # -- findings / citations ------------------------------------------
    def add_finding(
        self,
        session_id: str,
        sub_question: str | None,
        claim_text: str,
        confidence: float = 1.0,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO findings (session_id, sub_question, claim_text, confidence) "
                "VALUES (?, ?, ?, ?)",
                (session_id, sub_question, claim_text, confidence),
            )
            return int(cur.lastrowid)

    def add_citation(
        self,
        finding_id: int,
        url: str,
        title: str | None = None,
        author: str | None = None,
        publisher: str | None = None,
        formatted_apa: str | None = None,
        formatted_mla: str | None = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO citations
                    (finding_id, url, title, author, publisher, formatted_apa, formatted_mla)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (finding_id, url, title, author, publisher, formatted_apa, formatted_mla),
            )
            return int(cur.lastrowid)

    # -- memory pointers ------------------------------------------------
    def add_memory_pointer(
        self, session_id: str, chroma_vector_id: str, summary_text: str
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO memories (session_id, chroma_vector_id, summary_text) "
                "VALUES (?, ?, ?)",
                (session_id, chroma_vector_id, summary_text),
            )
            return int(cur.lastrowid)

    def get_memory_pointer(self, chroma_vector_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE chroma_vector_id = ?", (chroma_vector_id,)
            ).fetchone()
            return dict(row) if row else None

    # -- papers (derived from citations) ------------------------------------
    def get_session_papers(self, session_id: str) -> list[dict[str, Any]]:
        """Return all citation records associated with a session's findings."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.url, c.title, c.author, c.publisher,
                       c.formatted_apa, c.formatted_mla,
                       f.sub_question
                FROM citations c
                JOIN findings f ON f.finding_id = c.finding_id
                WHERE f.session_id = ?
                ORDER BY c.citation_id
                """,
                (session_id,),
            ).fetchall()

            # Also try to get papers from findings_json for richer data
            session = conn.execute(
                "SELECT findings_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            papers: list[dict[str, Any]] = []
            seen_urls: set[str] = set()

            # First: try findings_json (has full paper metadata)
            if session and session["findings_json"]:
                import json as _json
                try:
                    findings = _json.loads(session["findings_json"])
                    for f in findings:
                        for p in f.get("papers", []):
                            url = p.get("url", "")
                            if url and url not in seen_urls:
                                seen_urls.add(url)
                                papers.append({
                                    "title": p.get("title", ""),
                                    "author": p.get("author", ""),
                                    "publisher": p.get("venue", "") or p.get("publisher", ""),
                                    "url": url,
                                    "formatted_apa": p.get("summary", "") or p.get("abstract", ""),
                                    "sub_question": f.get("sub_question"),
                                })
                except (ValueError, TypeError):
                    pass

            # Fallback: relational citation rows
            if not papers:
                for row in rows:
                    r = dict(row)
                    url = r.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        papers.append(r)

            return papers
