# MCP-Powered Deep Research Agent
## Complete Technical Documentation

**Version:** 1.0
**Author:** [Your Name]
**Date:** August 2026
**Status:** Production-Ready Reference Implementation
**Cost to Build & Run:** $0.00 (100% free, open-source stack)

---

# TABLE OF CONTENTS

1. [Product Requirements Document (PRD)](#section-1-product-requirements-document-prd)
2. [Software Requirements Specification (SRS)](#section-2-software-requirements-specification-srs)
3. [Architecture Review](#section-3-architecture-review)
4. [Quality Assurance (QA) Plan](#section-4-quality-assurance-qa-plan)
5. [Acceptance Criteria & Failure Criteria](#section-5-acceptance-criteria--failure-criteria)
6. [Implementation Plan](#section-6-implementation-plan)
7. [Getting Started Guide](#section-7-getting-started-guide)
8. [Success Metrics](#section-8-success-metrics)

---

# SECTION 1: PRODUCT REQUIREMENTS DOCUMENT (PRD)

## 1.1 Executive Summary

The **MCP-Powered Deep Research Agent** is an autonomous, locally-run research assistant that performs multi-step web research, synthesizes findings from multiple sources, maintains persistent memory across sessions, and produces professionally cited, multi-format research outputs — all without a single paid API call.

The system is built around the **Model Context Protocol (MCP)**, exposing research capabilities (search, scrape, cite, summarize, remember) as discrete, composable tools that an LLM agent orchestrates via LangGraph. Because the underlying LLM runs locally through Ollama, the entire pipeline — from query decomposition to final report generation — has zero marginal cost and zero dependency on third-party rate limits or API keys.

This project demonstrates production-grade skills in: agentic system design, protocol-based tool architecture (MCP), local LLM orchestration, retrieval-augmented generation (RAG) with persistent vector memory, and full-stack delivery (CLI + web UI).

## 1.2 Product Vision

> "Give anyone a research analyst that never sleeps, never charges by the token, and never forgets what you asked it last week."

The agent should behave like a diligent junior research analyst: it takes an ambiguous question, breaks it into sub-questions, searches and reads multiple sources, cross-checks claims, cites everything properly, remembers the user's prior research threads, and delivers the output in whatever format best suits the task (a quick brief, a comparison chart, or a deep insight report).

## 1.3 Target Users

| User Segment | Primary Need | Example Use Case |
|---|---|---|
| **Students** | Fast, well-cited literature grounding | "Summarize the causes of the 2008 financial crisis with academic citations" |
| **Researchers** | Cross-session continuity, source traceability | Multi-week literature review where the agent recalls prior findings |
| **Professionals** | Competitive/market analysis under time pressure | "Compare the top 3 project management tools for a 50-person team" |
| **Content Creators** | Fact-checked briefs formatted for publishing | "Research and draft a briefing on quantum computing for a general audience" |

## 1.4 Core Features (Prioritized)

| ID | Feature | Priority | Description |
|---|---|---|---|
| F-01 | **MCP Tool Server** | P0 | Exposes search, scrape, cite, summarize, memory tools via FastMCP |
| F-02 | **Multi-Step Research Agent** | P0 | LangGraph state machine that plans, searches, reads, and synthesizes |
| F-03 | **Citation Engine** | P0 | Generates APA/MLA formatted, clickable citations for every claim |
| F-04 | **Multi-Format Output** | P0 | Markdown Briefs, Comparison Charts, Insight Reports from one pipeline |
| F-05 | **Persistent Memory Module** | P0 | ChromaDB + SQLite cross-session recall via embeddings |
| F-06 | **CLI Interface** | P1 | Terminal-based interaction for power users and scripting |
| F-07 | **Streamlit Web UI** | P1 | Visual interface with session history and export buttons |

## 1.5 Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Performance** | A typical 3-source research query completes in under 90 seconds on an 8-core CPU / 16GB RAM machine with a 7B-parameter local model. |
| **Scalability** | Stateless MCP tool design allows horizontal scaling of scraper workers; SQLite is sufficient for single-user use but the schema is Postgres-portable. |
| **Reliability** | Agent must gracefully degrade (partial results + warning) rather than crash on a single failed source. |
| **Usability** | A first-time user must be able to run a query within 5 minutes of cloning the repo, per the Getting Started Guide. |
| **Security** | No credentials stored in plaintext; scraping respects robots.txt; no arbitrary code execution from LLM output. |
| **Cost** | $0 recurring cost — no paid LLM API, no paid search API, no paid hosting required for local use. |
| **Offline Capability** | Once sources are cached, previously-researched topics can be re-summarized fully offline using cached embeddings. |

## 1.6 Constraints & Assumptions

**Constraints:**
- Must run entirely on consumer hardware (no GPU required, though GPU accelerates inference).
- Must use only free/open-source libraries and free-tier-less search (DuckDuckGo has no API key requirement for the `duckduckgo-search` package).
- No telemetry or data leaves the user's machine.

**Assumptions:**
- User has Python 3.10+ and ~8GB free disk space (for Ollama model weights).
- User has a stable internet connection for the search/scrape phase (research itself cannot be fully offline; only re-summarization of cached content can).
- DuckDuckGo's HTML search endpoint remains scrapeable without authentication (this is a documented risk — see Section 5, FC-08).

---

# SECTION 2: SOFTWARE REQUIREMENTS SPECIFICATION (SRS)

## 2.1 Introduction

### Purpose
This SRS defines the functional and technical requirements for the MCP-Powered Deep Research Agent, covering the MCP server, the LangGraph agent, the memory subsystem, and both user interfaces.

### Scope
In scope: query decomposition, web search, scraping, citation generation, embedding-based memory, multi-format report generation, CLI, Streamlit UI.
Out of scope: multi-user authentication, cloud deployment, paid-API integrations, mobile clients.

## 2.2 System Architecture

### 2.2.1 High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                            USER INTERFACES                            │
│  ┌───────────────────┐              ┌────────────────────────────┐   │
│  │   CLI (Typer)      │              │   Streamlit Web UI          │   │
│  └──────────┬─────────┘              └───────────────┬────────────┘   │
└─────────────┼─────────────────────────────────────────┼───────────────┘
              │                                          │
              └───────────────────┬──────────────────────┘
                                   ▼
                    ┌──────────────────────────────┐
                    │   LangGraph Orchestrator       │
                    │  (Planner → Researcher →       │
                    │   Synthesizer → Formatter)      │
                    └───────────────┬───────────────┘
                                    │  MCP Client calls
                                    ▼
                    ┌──────────────────────────────┐
                    │        FastMCP Server          │
                    │  Tools:                        │
                    │  - web_search                  │
                    │  - scrape_page                 │
                    │  - generate_citation           │
                    │  - store_memory / recall_memory│
                    │  - format_output               │
                    └───────┬─────────────┬──────────┘
                            │             │
              ┌─────────────┘             └─────────────┐
              ▼                                          ▼
   ┌───────────────────────┐                  ┌────────────────────────┐
   │  Web Layer              │                  │  Memory Layer            │
   │  - duckduckgo-search    │                  │  - SQLite (structured)   │
   │  - BeautifulSoup4        │                  │  - ChromaDB (vector)     │
   │  - Playwright (JS pages) │                  │  - Ollama embeddings     │
   └───────────────────────┘                  └────────────────────────┘
                            │
                            ▼
                 ┌────────────────────────┐
                 │   Ollama (Local LLM)     │
                 │   e.g. llama3.1:8b       │
                 └────────────────────────┘
```

### 2.2.2 Component Breakdown Table

| Component | Technology | Purpose | Cost |
|---|---|---|---|
| Tool Server | FastMCP | Exposes research capabilities as MCP tools | $0 |
| Agent Orchestration | LangGraph | Stateful multi-step reasoning graph | $0 |
| LLM Inference | Ollama (llama3.1:8b / qwen2.5:7b) | Local reasoning, synthesis, citation drafting | $0 |
| Web Search | duckduckgo-search | Query-to-URL retrieval, no API key | $0 |
| Static Scraping | BeautifulSoup4 + httpx | Parse simple HTML pages | $0 |
| Dynamic Scraping | Playwright | Render JS-heavy pages | $0 |
| Structured Memory | SQLite | Sessions, findings, citations | $0 |
| Vector Memory | ChromaDB | Embedding-based semantic recall | $0 |
| Embeddings | Ollama (nomic-embed-text) | Local embedding generation | $0 |
| CLI | Typer + Rich | Terminal interaction | $0 |
| Web UI | Streamlit | Browser-based interaction | $0 |
| CI/CD | GitHub Actions (public repo) | Automated testing | $0 |

## 2.3 Functional Requirements

### 2.3.1 MCP Server Requirements

| ID | Requirement |
|---|---|
| MCP-01 | Server SHALL expose a `web_search(query: str, max_results: int)` tool returning title, URL, snippet. |
| MCP-02 | Server SHALL expose a `scrape_page(url: str)` tool returning cleaned text content, falling back to Playwright if static scraping yields <200 characters. |
| MCP-03 | Server SHALL expose a `generate_citation(source: dict, style: Literal["apa","mla"])` tool returning a formatted citation string. |
| MCP-04 | Server SHALL expose a `store_memory(session_id: str, content: str, metadata: dict)` tool that embeds and persists content to ChromaDB. |
| MCP-05 | Server SHALL expose a `recall_memory(session_id: str, query: str, top_k: int)` tool returning semantically relevant past findings. |
| MCP-06 | Server SHALL expose a `format_output(findings: list, format: Literal["brief","comparison","report"])` tool. |
| MCP-07 | All tools SHALL return structured JSON-serializable responses, never raw exceptions. |
| MCP-08 | Server SHALL log every tool invocation (tool name, args, duration, success/failure) to a local log file. |
| MCP-09 | Server SHALL enforce a per-tool timeout (default 30s for scraping, 10s for search) to prevent agent hangs. |

### 2.3.2 Agent Requirements

| ID | Requirement |
|---|---|
| AG-01 | Agent SHALL decompose a complex user query into 2–5 sub-questions before searching. |
| AG-02 | Agent SHALL call `web_search` for each sub-question and select the top 3 most relevant results by title/snippet relevance. |
| AG-03 | Agent SHALL scrape and read each selected source before drafting any claim. |
| AG-04 | Agent SHALL attach a citation to every factual claim in its output. |
| AG-05 | Agent SHALL check `recall_memory` at the start of every session for relevant prior findings before searching the web again. |
| AG-06 | Agent SHALL store new findings via `store_memory` at the end of every research session. |
| AG-07 | Agent SHALL degrade gracefully — if a source fails to scrape, it SHALL proceed with remaining sources and note the omission. |

### 2.3.3 Memory Module Requirements

| ID | Requirement |
|---|---|
| MEM-01 | System SHALL persist all findings in SQLite with foreign-key relations to sessions and citations. |
| MEM-02 | System SHALL generate embeddings for every stored finding using a local embedding model. |
| MEM-03 | System SHALL support semantic similarity search with a configurable relevance threshold (default cosine similarity ≥ 0.75). |
| MEM-04 | System SHALL allow a user to list, search, and delete past research sessions. |
| MEM-05 | Memory SHALL persist across process restarts (no in-memory-only storage). |

### 2.3.4 Output Requirements

| ID | Requirement |
|---|---|
| OUT-01 | System SHALL support a **Markdown Brief** format: 1-page summary with headline findings and citations. |
| OUT-02 | System SHALL support a **Comparison Chart** format: Markdown table comparing entities across attributes. |
| OUT-03 | System SHALL support an **Insight Report** format: multi-section long-form report with executive summary, findings, and references. |
| OUT-04 | Every output format SHALL include a References section with full citations in the requested style. |

## 2.4 User Interface Requirements

### 2.4.1 CLI Commands

```bash
# Run a new research query
research ask "What are the trade-offs between REST and GraphQL?" --format report

# List past sessions
research sessions list

# Resume / recall a past session
research sessions recall <session_id> --query "follow up on caching strategy"

# Export last result
research export --format apa --output findings.md
```

### 2.4.2 Streamlit Web Interface

The web UI provides: a query input box, a live "agent thinking" trace panel showing each tool call as it happens, a format selector (Brief / Comparison / Report), a session sidebar listing past research threads with semantic search, and one-click export to Markdown or PDF.

## 2.5 Database Schema

```sql
-- sessions: one row per research session
CREATE TABLE sessions (
    session_id      TEXT PRIMARY KEY,
    user_query      TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    output_format   TEXT CHECK(output_format IN ('brief','comparison','report')),
    status          TEXT CHECK(status IN ('running','completed','failed')) DEFAULT 'running'
);

-- findings: individual synthesized claims tied to a session
CREATE TABLE findings (
    finding_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(session_id),
    sub_question    TEXT,
    claim_text      TEXT NOT NULL,
    confidence      REAL DEFAULT 1.0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- citations: source metadata linked to findings
CREATE TABLE citations (
    citation_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id      INTEGER NOT NULL REFERENCES findings(finding_id),
    url             TEXT NOT NULL,
    title           TEXT,
    author          TEXT,
    publisher       TEXT,
    accessed_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    formatted_apa   TEXT,
    formatted_mla   TEXT
);

-- memories: pointer table linking SQLite records to ChromaDB vector IDs
CREATE TABLE memories (
    memory_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(session_id),
    chroma_vector_id TEXT NOT NULL UNIQUE,
    summary_text    TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 2.6 API Specifications (MCP Tool Definitions)

```python
from fastmcp import FastMCP
from typing import Literal
from pydantic import BaseModel

mcp = FastMCP("deep-research-agent")

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str

@mcp.tool()
def web_search(query: str, max_results: int = 5) -> list[SearchResult]:
    """
    Search the web via DuckDuckGo (no API key required).

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 5).

    Returns:
        A list of SearchResult objects with title, url, and snippet.
    """
    ...

@mcp.tool()
def scrape_page(url: str) -> dict:
    """
    Fetch and extract clean text content from a web page.
    Falls back to Playwright rendering if static extraction yields
    less than 200 characters of usable text.

    Args:
        url: The full URL to scrape.

    Returns:
        dict with keys: url, title, text, word_count, method_used.
    """
    ...

@mcp.tool()
def generate_citation(source: dict, style: Literal["apa", "mla"] = "apa") -> str:
    """
    Generate a formatted citation string for a given source.

    Args:
        source: dict with keys url, title, author (optional), publisher (optional).
        style: Citation style, either 'apa' or 'mla'.

    Returns:
        A formatted citation string.
    """
    ...

@mcp.tool()
def store_memory(session_id: str, content: str, metadata: dict) -> dict:
    """
    Embed and persist a piece of research content for future recall.

    Args:
        session_id: Identifier of the current research session.
        content: The text content to remember.
        metadata: Arbitrary metadata (topic, source_url, etc).

    Returns:
        dict confirming storage with the generated vector ID.
    """
    ...

@mcp.tool()
def recall_memory(session_id: str, query: str, top_k: int = 5) -> list[dict]:
    """
    Retrieve semantically relevant past findings for a query.

    Args:
        session_id: Session to scope the recall to (or 'all' for global recall).
        query: The text to find semantically similar memories for.
        top_k: Number of results to return.

    Returns:
        A list of dicts with content, similarity_score, and original session_id.
    """
    ...

@mcp.tool()
def format_output(findings: list[dict], format: Literal["brief", "comparison", "report"]) -> str:
    """
    Render findings into one of three output formats.

    Args:
        findings: List of finding dicts (claim, citations, sub_question).
        format: One of 'brief', 'comparison', or 'report'.

    Returns:
        A fully formatted Markdown string ready for export.
    """
    ...
```

---

# SECTION 3: ARCHITECTURE REVIEW

## 3.1 Component Flow Diagram

```
User Query
    │
    ▼
┌─────────────┐     decomposes into sub-questions
│   Planner    │────────────────────────────────┐
└─────────────┘                                  │
                                                  ▼
                                     ┌──────────────────────┐
                                     │  For each sub-question │
                                     │  (loop)                │
                                     └───────────┬────────────┘
                                                  │
                       ┌──────────────────────────┼──────────────────────────┐
                       ▼                          ▼                          ▼
              recall_memory()             web_search()               (if new info needed)
                       │                          │                          │
                       └──────────────┬───────────┴──────────────────────────┘
                                      ▼
                            scrape_page() for top sources
                                      │
                                      ▼
                          LLM synthesizes claim + evidence
                                      │
                                      ▼
                          generate_citation() per source
                                      │
                                      ▼
                          store_memory() for future recall
                                      │
                                      ▼
                          (loop ends when all sub-Qs resolved)
                                      │
                                      ▼
                            format_output(findings, format)
                                      │
                                      ▼
                          Return Brief / Comparison / Report
```

## 3.2 Detailed Data Flow Table

| Step | Action | Component | Data |
|---|---|---|---|
| 1 | User submits query | CLI / Streamlit | Raw query string |
| 2 | Query decomposed into sub-questions | LangGraph Planner node | List[str] sub-questions |
| 3 | Check memory for relevant past findings | recall_memory MCP tool | Query embedding → top-k matches |
| 4 | Search web for each unresolved sub-question | web_search MCP tool | List[SearchResult] |
| 5 | Scrape top 3 results per sub-question | scrape_page MCP tool | Cleaned text per URL |
| 6 | LLM drafts claim grounded in scraped text | Ollama via LangGraph | Claim text + source mapping |
| 7 | Generate formatted citation per source | generate_citation MCP tool | APA/MLA string |
| 8 | Persist finding + citation | SQLite (findings, citations tables) | Structured rows |
| 9 | Embed and store finding for future recall | store_memory → ChromaDB | Vector + metadata |
| 10 | Render final output in requested format | format_output MCP tool | Markdown Brief/Comparison/Report |
| 11 | Return to user via CLI/UI | CLI / Streamlit | Rendered Markdown + export option |

## 3.3 Design Decisions & Rationale

### Why Local LLM (Ollama)?
Running inference locally eliminates per-token cost entirely, removes rate-limit dependencies on third-party providers, and keeps all research content on the user's machine — a meaningful privacy property for sensitive research topics. The trade-off is lower raw reasoning quality versus frontier hosted models, mitigated by keeping the agent's reasoning steps small and well-scoped (decomposition, single-claim synthesis) rather than asking the model to reason over very long contexts in one shot.

### Why FastMCP?
MCP standardizes how an agent discovers and calls tools, which decouples the "brain" (LangGraph orchestration) from the "hands" (search, scrape, cite, remember). This means the tool server can be swapped, extended, or reused by a completely different agent framework without rewriting tool logic — a property plain function-calling setups don't give you. FastMCP specifically was chosen because it lets tools be defined as plain, type-hinted Python functions with docstrings, which the framework auto-converts into MCP tool schemas.

### Why LangGraph (over a simple loop or LangChain AgentExecutor)?
The research process is naturally a state machine (Plan → Research loop → Synthesize → Format), not a single linear chain. LangGraph makes each state explicit, allows conditional branching (e.g., skip web search if memory recall is sufficient), and makes the "agent thinking trace" shown in the Streamlit UI a natural byproduct of graph execution rather than something bolted on.

## 3.4 Security Architecture

| Layer | Control |
|---|---|
| 1. Input Handling | User queries are treated as data, never executed; no `eval`/`exec` on LLM or user output. |
| 2. Scraping Ethics | robots.txt is checked before scraping; a descriptive User-Agent identifies the bot; rate limiting prevents hammering any single domain. |
| 3. Tool Sandboxing | MCP tools run with least privilege — scraping tools have no filesystem write access outside a designated cache directory. |
| 4. Output Sanitization | Scraped HTML is stripped of scripts/styles before being passed to the LLM to prevent prompt injection from malicious pages. |
| 5. Local-Only Data | No research content, embeddings, or session data ever leaves the local machine; no analytics/telemetry calls. |

## 3.5 Technology Stack Justification Table

| Component | Technology | Version | Reasoning |
|---|---|---|---|
| Language | Python | 3.11 | Best-supported ecosystem for LLM tooling |
| Tool Protocol | FastMCP | 2.x | Fast, decorator-based MCP server implementation |
| Orchestration | LangGraph | 0.2.x | Explicit state machine for multi-step agents |
| LLM Runtime | Ollama | 0.3.x | Simplest local model serving, OpenAI-compatible API |
| Default Model | llama3.1:8b | — | Best free reasoning/size trade-off for 16GB RAM machines |
| Embedding Model | nomic-embed-text | — | Free, local, strong retrieval performance |
| Search | duckduckgo-search | 6.x | No API key, generous free usage |
| Static Scraping | httpx + BeautifulSoup4 | 4.12.x | Fast, reliable for non-JS pages |
| Dynamic Scraping | Playwright | 1.4x | Handles JS-rendered pages headlessly |
| Structured Store | SQLite (stdlib) | 3.4x | Zero-config, file-based, ACID-compliant |
| Vector Store | ChromaDB | 0.5.x | Local-first embedded vector DB, no server needed |
| CLI Framework | Typer + Rich | latest | Ergonomic CLI with progress bars/tables |
| Web UI | Streamlit | 1.3x | Fastest path to a usable data-app UI |
| CI | GitHub Actions | — | Free for public repos |
| Testing | pytest + pytest-asyncio | latest | Standard async-friendly test framework |

## 3.6 Alternative Options Considered

| Considered | Rejected Because |
|---|---|
| OpenAI/Anthropic hosted API | Violates $0-cost constraint; introduces per-token billing risk |
| SerpAPI / Google Custom Search API | Requires paid tier beyond small free quota; API key management overhead |
| Postgres for memory store | Requires a running server process; SQLite is sufficient for single-user scope |
| Pinecone/Weaviate cloud vector DB | Paid or requires hosted infra; ChromaDB's embedded mode needs neither |
| Plain LangChain `AgentExecutor` | Less transparent control flow than LangGraph; harder to expose a live "thinking trace" |
| Scrapy | Heavier framework than needed for a handful of pages per query; BeautifulSoup + Playwright is simpler to reason about |

---

# SECTION 4: QUALITY ASSURANCE (QA) PLAN

## 4.1 Testing Strategy — Test Pyramid

```
                 ▲
                / \        E2E Tests (10%)
               /---\       — Full query → report, real network
              /     \
             /-------\     Integration Tests (30%)
            /         \    — MCP tools + agent graph, mocked network
           /-----------\
          /             \  Unit Tests (60%)
         /---------------\ — Individual functions, fully mocked
```

## 4.2 Unit Tests

| Component | Test Cases | Priority |
|---|---|---|
| `web_search` | Returns list of correct length; handles zero results; handles network timeout | P0 |
| `scrape_page` | Extracts text from static HTML; falls back to Playwright on thin content; handles 404/500 | P0 |
| `generate_citation` | Correct APA format; correct MLA format; handles missing author gracefully | P0 |
| `store_memory` / `recall_memory` | Round-trip store→recall returns original content; similarity threshold filters irrelevant results | P0 |
| `format_output` | Each of 3 formats produces valid Markdown; empty findings list handled | P1 |
| SQLite schema | Foreign key constraints enforced; cascading queries return expected joins | P1 |

## 4.3 Integration Tests

| Scenario | Expected Outcome |
|---|---|
| Full MCP tool chain: search → scrape → cite | Citation references the correct scraped URL and title |
| Agent recall-before-search | If memory recall confidence ≥ threshold, `web_search` is skipped for that sub-question |
| Partial source failure | If 1 of 3 sources fails to scrape, session still completes with 2 sources and a logged warning |
| Cross-session memory | A finding stored in session A is retrievable by a semantically similar query in session B |

## 4.4 End-to-End Tests

| ID | Test Case |
|---|---|
| E2E-01 | Simple factual query → Markdown Brief produced with ≥1 citation |
| E2E-02 | Comparison query ("X vs Y vs Z") → Comparison Chart with all three entities as columns |
| E2E-03 | Complex multi-part query → Insight Report with all sub-questions addressed in separate sections |
| E2E-04 | Repeat query in new session → response time reduced due to memory recall (no redundant scraping) |
| E2E-05 | CLI and Streamlit UI produce equivalent output for the identical query |

## 4.5 Performance Testing

### Performance Metrics Table

| Metric | Target |
|---|---|
| Simple query (1 sub-question) latency | < 30s |
| Complex query (4-5 sub-questions) latency | < 120s |
| Memory recall latency | < 500ms |
| Citation generation latency | < 100ms per source |
| Embedding generation (per finding) | < 1s on CPU |
| Concurrent session support | ≥ 3 simultaneous sessions without deadlock |
| SQLite query latency (session history) | < 50ms for 10k rows |

### Resource Utilization Table

| Resource | Expected Usage |
|---|---|
| RAM (idle) | ~500MB (server + UI) |
| RAM (during 8B model inference) | 6–8GB |
| Disk (model weights) | ~5GB for llama3.1:8b |
| Disk (per 100 research sessions) | < 50MB (SQLite + Chroma) |
| CPU | 4+ cores recommended for acceptable inference speed |

## 4.6 Reliability Testing

| Failure Scenario | Response Strategy |
|---|---|
| Search provider returns zero results | Agent notifies user, suggests query rephrasing |
| Target page blocks scraping (403/robots.txt) | Skip source, log, continue with remaining sources |
| Ollama server not running | Fail fast with a clear setup instruction, not a stack trace |
| ChromaDB corruption/lock | Fallback to SQLite-only mode (structured recall without semantic search) |
| Playwright browser crash | Retry once, then fall back to static scrape (best-effort) |

## 4.7 Usability Testing

**Acceptance metrics:** a first-time user completes a query end-to-end without external help in under 5 minutes; ≥90% of test users correctly interpret the citation format without explanation; the "agent thinking trace" is rated "clear" or "very clear" by ≥80% of test users.

## 4.8 Continuous Integration

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Install Playwright browsers
        run: playwright install --with-deps chromium

      - name: Lint (ruff)
        run: ruff check .

      - name: Type check (mypy)
        run: mypy src/

      - name: Run unit tests
        run: pytest tests/unit --cov=src --cov-report=xml

      - name: Run integration tests (mocked network)
        run: pytest tests/integration

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
```

---

# SECTION 5: ACCEPTANCE CRITERIA & FAILURE CRITERIA

## Part A: Acceptance Criteria (Must Have ALL)

### Functional

| ID | Criterion | Validation Method |
|---|---|---|
| AC-01 | Agent decomposes complex queries into sub-questions | Unit test on Planner node |
| AC-02 | Every claim in output has a matching citation | Automated check: claim count vs citation count parity |
| AC-03 | All three output formats render valid Markdown | Markdown linter on generated output |
| AC-04 | Memory persists across process restart | Integration test: kill process, restart, recall |
| AC-05 | CLI supports ask, sessions list, sessions recall, export | CLI smoke test suite |
| AC-06 | Streamlit UI mirrors CLI functionality | Manual UX walkthrough + E2E-05 |
| AC-07 | Citations correctly formatted in both APA and MLA | Unit tests against known citation examples |
| AC-08 | Agent gracefully handles a failed source | Integration test with mocked 500 error |
| AC-09 | Semantic recall retrieves relevant, not just recent, memories | Integration test with dissimilar-content decoy |
| AC-10 | System requires zero API keys for paid services | Manual audit of `.env.example` and dependency list |

### Performance

| ID | Criterion | Validation Method |
|---|---|---|
| AC-11 | Simple query completes in < 30s | Automated performance test |
| AC-12 | Complex query completes in < 120s | Automated performance test |
| AC-13 | Memory recall completes in < 500ms | Automated performance test |
| AC-14 | System supports ≥3 concurrent sessions | Load test script |

### Quality

| ID | Criterion | Validation Method |
|---|---|---|
| AC-15 | ≥80% unit test coverage on `src/` | CI coverage report |
| AC-16 | Zero critical lint errors (ruff) | CI lint job |
| AC-17 | Zero type errors (mypy strict on core modules) | CI type-check job |
| AC-18 | All MCP tools have complete docstrings | Automated docstring presence check |

### Documentation

| ID | Criterion | Validation Method |
|---|---|---|
| AC-19 | README enables setup in < 5 minutes | Fresh-machine walkthrough test |
| AC-20 | All environment variables documented | Manual audit vs `.env.example` |
| AC-21 | Architecture diagrams present and accurate | Peer review |
| AC-22 | API/tool specifications match actual implementation | Automated schema diff test |

## Part B: Failure Criteria (Project FAILS if ANY occur)

### Critical Failure

| ID | Criterion | Resolution Strategy |
|---|---|---|
| FC-01 | Agent produces claims with zero citations | Block release; add citation-parity CI gate |
| FC-02 | System requires any paid API key to function | Remove/replace the dependency before release |
| FC-03 | Memory data loss on normal restart | Fix persistence layer; add restart integration test to CI |
| FC-04 | Agent executes arbitrary code from scraped content | Add sanitization layer; security review before release |
| FC-05 | System crashes (unhandled exception) on a single bad source | Wrap all tool calls in try/except with structured error return |
| FC-06 | Citations reference the wrong source | Add source-ID tracing through the pipeline; regression test |
| FC-07 | Complete pipeline failure with no partial output | Implement graceful degradation at every stage |

### Performance Failure

| ID | Criterion | Resolution Strategy |
|---|---|---|
| FC-08 | Simple query exceeds 60s consistently | Profile bottleneck (usually scraping or model load); consider caching model in memory |
| FC-09 | Memory recall exceeds 2s | Add ChromaDB indexing/tuning; reduce embedding dimensionality if needed |
| FC-10 | RAM usage exceeds 12GB on default config | Switch default model to a smaller quantized variant |

### Quality Failure

| ID | Criterion | Resolution Strategy |
|---|---|---|
| FC-11 | Unit test coverage drops below 70% | Block merge via CI coverage gate |
| FC-12 | Citation format fails validation against style guide | Fix formatter; add golden-file regression tests |
| FC-13 | Documentation is out of sync with actual API | Add doc-drift check to CI (schema vs docstring diff) |

### Risk-Based Failure Criteria Table

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| DuckDuckGo scraping endpoint changes/blocks requests | Medium | High | Abstract search behind an interface; add a secondary free search fallback (e.g., searx instance) |
| Local model produces hallucinated claims not grounded in scraped text | Medium | High | Enforce a "claim must quote/paraphrase from provided context" prompting constraint; add a groundedness check step |
| Target sites block scraping via anti-bot measures | High | Medium | Respect robots.txt; degrade to search-snippet-only synthesis when scraping fails |
| ChromaDB index grows unbounded over long-term use | Low | Medium | Add periodic pruning/archival of old low-relevance memories |
| User's machine lacks sufficient RAM for 8B model | Medium | Medium | Document smaller model fallback (e.g., phi3:mini) in Getting Started Guide |

---

# SECTION 6: IMPLEMENTATION PLAN

## Phase 1: Core Infrastructure (Week 1)

| Task | Estimate |
|---|---|
| Set up repo structure, `pyproject.toml`, dependency management | 3h |
| Implement FastMCP server skeleton with tool stubs | 4h |
| Implement `web_search` and `scrape_page` tools with error handling | 6h |
| Set up SQLite schema + migration script | 3h |
| Set up ChromaDB + Ollama embedding integration | 4h |

## Phase 2: Agent Orchestration (Week 2)

| Task | Estimate |
|---|---|
| Design LangGraph state machine (Planner/Researcher/Synthesizer/Formatter nodes) | 6h |
| Implement MCP client integration inside LangGraph nodes | 5h |
| Implement `generate_citation` tool (APA + MLA) | 4h |
| Implement `store_memory` / `recall_memory` tools end-to-end | 5h |

## Phase 3: Advanced Features (Week 3)

| Task | Estimate |
|---|---|
| Implement `format_output` for all 3 formats (Brief, Comparison, Report) | 6h |
| Add graceful-degradation logic for failed sources | 3h |
| Add recall-before-search short-circuit logic | 3h |
| Write unit + integration test suite, wire up CI | 6h |

## Phase 4: UI & Polish (Week 4)

| Task | Estimate |
|---|---|
| Build Typer CLI (`ask`, `sessions list/recall`, `export`) | 5h |
| Build Streamlit UI with live agent-trace panel | 6h |
| Write README, architecture docs, and Getting Started Guide | 4h |
| Performance tuning + final E2E test pass | 4h |

**Total estimated effort:** ~68 hours over 4 weeks (part-time pace).

---

# SECTION 7: GETTING STARTED GUIDE

## 7.1 Prerequisites

```bash
# Python 3.10+
python3 --version

# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull required local models
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## 7.2 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-deep-research-agent.git
cd mcp-deep-research-agent

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium

# Initialize the database
python scripts/init_db.py

# Copy and configure environment file
cp .env.example .env
```

## 7.3 Running the Agent

```bash
# Start the MCP server (in one terminal)
python -m src.mcp_server

# CLI usage (in another terminal)
research ask "Compare React, Vue, and Svelte for a small team" --format comparison

# Or launch the Streamlit UI
streamlit run src/ui/app.py
```

## 7.4 Complete Project Structure

```
mcp-deep-research-agent/
├── README.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml
├── scripts/
│   └── init_db.py
├── src/
│   ├── mcp_server.py
│   ├── tools/
│   │   ├── search.py
│   │   ├── scrape.py
│   │   ├── citation.py
│   │   ├── memory.py
│   │   └── formatter.py
│   ├── agent/
│   │   ├── graph.py
│   │   ├── nodes/
│   │   │   ├── planner.py
│   │   │   ├── researcher.py
│   │   │   ├── synthesizer.py
│   │   │   └── formatter.py
│   │   └── state.py
│   ├── memory/
│   │   ├── sqlite_store.py
│   │   └── vector_store.py
│   ├── cli/
│   │   └── main.py
│   └── ui/
│       └── app.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── data/
    ├── research.db
    └── chroma/
```

---

# SECTION 8: SUCCESS METRICS

| Metric | Target | Measurement Method |
|---|---|---|
| Citation accuracy | 100% of claims traceable to a real scraped source | Automated claim-to-citation trace audit |
| Setup time (new user) | < 5 minutes to first successful query | Fresh-machine timed walkthrough |
| Query latency (simple) | < 30 seconds | Automated performance test suite |
| Memory recall relevance | ≥ 90% of recalled items rated relevant by manual review | Sampled manual review of 50 recall events |
| Test coverage | ≥ 80% on core modules | CI coverage report |
| **Total operating cost** | **$0.00** | Manual audit: no paid API keys, no paid hosting, no metered services in dependency tree |

**Cost Verification:** Every dependency in `requirements.txt` is open-source and free to use (MIT/Apache-2.0/BSD licensed). Ollama, DuckDuckGo search (via the unofficial free package), SQLite, and ChromaDB's embedded mode all run entirely on local hardware with no metered billing surface. GitHub Actions CI is free for public repositories under standard usage limits.

---

*End of Documentation.*
