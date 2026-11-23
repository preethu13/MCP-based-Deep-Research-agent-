# ARCHITECTURE.md — System Architecture & Data Flow

> **Repository:** MCP-Powered Deep Research Agent  
> **Documentation Version:** 1.0 (Live Implementation State)  

---

## 1. High-Level Architecture Diagram

```
                 +-------------------------------------------------------+
                 |                    User Interfaces                    |
                 |      Streamlit UI (Port 8501)   /   Typer CLI         |
                 +---------------------------+---------------------------+
                                             |
                                             v
                 +-------------------------------------------------------+
                 |              LangGraph Orchestration Engine           |
                 |                                                       |
                 |  START -> [Planner] -> [Researcher] -> [Synthesizer]  |
                 |                     -> [Formatter] -> END             |
                 +---------------------------+---------------------------+
                                             |
                   +-------------------------+-------------------------+
                   |                                                   |
                   v (In-Process Calls)                                v (Remote RPC)
     +---------------------------+                       +---------------------------+
     |   ToolClient (In-Process) |                       | FastMCP Server (Optional) |
     |   (src/agent/tool_client) |                       | (src/mcp_server.py)       |
     +-------------+-------------+                       +-------------+-------------+
                   |                                                   |
       +-----------+-----------+                           +-----------+-----------+
       |           |           |                           |           |           |
       v           v           v                           v           v           v
  [OpenAlex]     [DDGS]    [Scraper]                   [OpenAlex]    [DDGS]    [Scraper]
  (Academic)     (Web)     (HTML/JS)                   (Academic)    (Web)     (HTML/JS)
       |           |           |                           |           |           |
       +-----------+-----------+                           +-----------+-----------+
                   |                                                   |
                   +-------------------------+-------------------------+
                                             |
                                             v
                 +-------------------------------------------------------+
                 |                   Persistence Layer                   |
                 |    SQLite (Structured)    |   ChromaDB (Vector)       |
                 |    (data/research.db)     |   (data/chroma)           |
                 +---------------------------+---------------------------+
                                             |
                                             v
                 +-------------------------------------------------------+
                 |                    Inference Engines                  |
                 |  Local Ollama (llama3.1)  |  Cloud API (OpenRouter)   |
                 +-------------------------------------------------------+
```

---

## 2. Agent Node Responsibilities

The agent is compiled into a deterministic StateGraph in `src/agent/graph.py`. Each node is an isolated Python function operating on `ResearchState`:

### 1. Planner Node (`src/agent/nodes/planner.py`)
- **Input:** `state["query"]`, `state["output_format"]`
- **Responsibility:** Decomposes the research topic into 2–3 focused, non-overlapping sub-questions.
- **Prompt Guard:** Directs the LLM to return strict JSON arrays and explicitly preserve subject keywords.
- **Degradation:** If the LLM produces invalid JSON or is unreachable, falls back to `_heuristic_decompose()` (regex splitting on delimiters like `vs`, commas, or conjunctions).
- **Output:** `sub_questions: list[str]`

### 2. Researcher Node (`src/agent/nodes/researcher.py`)
- **Input:** `state["sub_questions"]`, `state["query"]`
- **Responsibility:** Multi-source literature retrieval and content extraction.
  1. **Recall-Before-Search:** Calls `deps.tools.recall_memory("all", sub_q)`. If $\ge 2$ strong matches exist, marks `used_memory = True` and skips web search.
  2. **Query Cleaning:** Runs `clean_search_query(sub_q, main_query)` to strip question stopwords.
  3. **Multi-Source Retrieval:** Calls OpenAlex (`search_academic_papers`) and DuckDuckGo (`web_search`).
  4. **Relevance Scoring:** Runs `score_paper_relevance()` against each candidate; filters out items scoring $<0.5$.
  5. **Concurrent Extraction:** For papers with full abstracts in OpenAlex, extracts them immediately (fast-path). For web URLs, scrapes text concurrently via `ThreadPoolExecutor` (capping workers at 5).
- **Output:** `research: list[dict[str, Any]]` containing gathered contexts and metadata.

### 3. Synthesizer Node (`src/agent/nodes/synthesizer.py`)
- **Input:** `state["research"]`, `state["session_id"]`
- **Responsibility:** Grounded claim generation and database persistence.
  1. **Batch Synthesis:** Groups all sub-questions and contexts into one structured prompt (`_batch_synthesize_claims`), generating all findings in a single LLM pass.
  2. **Relational Storage:** Inserts each finding into SQLite (`findings` table) and associates every source URL into the `citations` table.
  3. **Vector Memory:** Computes embeddings and inserts each synthesized claim into ChromaDB (`research_memories` collection) linked by session ID.
- **Output:** `findings: list[dict[str, Any]]`

### 4. Formatter Node (`src/agent/nodes/formatter.py`)
- **Input:** `state["findings"]`, `state["output_format"]`, `state["citation_style"]`
- **Responsibility:** Document compilation and bibliographic citation formatting.
  1. Resolves citation styles (APA-7th or MLA-9th) via `src/tools/citation.py`.
  2. Formats the core body (Executive Brief, Comparison Matrix, or Deep Report).
  3. Formats the dedicated **"Research Papers & Literature"** section with clickable DOI/PDF links, publication years, and author rosters.
  4. Formats the **"References"** section with formal alphabetical bibliographic entries.
- **Output:** `final_output: str` (Markdown string ready for UI/CLI presentation).

---

## 3. LangGraph State Management (`ResearchState`)

The state schema (`src/agent/state.py`) is threaded through all nodes:

```python
class ResearchState(TypedDict, total=False):
    # Inputs
    query: str
    output_format: str          # "brief" | "comparison" | "report"
    citation_style: str         # "apa" | "mla"
    session_id: str

    # Working State
    sub_questions: list[str]
    research: list[dict[str, Any]]   # Raw sources, abstracts, memory hits
    findings: list[dict[str, Any]]   # Synthesized claims + linked citation objects

    # Observability
    trace: list[dict[str, Any]]      # Chronological timeline of tool events
    warnings: list[str]              # Non-fatal warnings

    # Output
    final_output: str                # Final compiled markdown document
```

### Telemetry & Live Trace
Every node emits events via `make_event(step, node, tool, title, detail, status)`. The Streamlit UI subscribes to `ResearchAgent.stream()`, reading `trace` updates to render live activity feeds without blocking.

---

## 4. MCP Servers vs. In-Process Tool Execution

The codebase provides two access patterns for tools:

### In-Process: `src/agent/tool_client.py`
- Used directly by LangGraph agent nodes.
- Calls tool functions directly in Python without inter-process communication (IPC) overhead.
- Includes exception shielding: tools return fallback data structures rather than crashing.

### External MCP Server: `src/mcp_server.py`
- Exposes tools via FastMCP over standard I/O (stdio) for external hosts (such as Claude Desktop).
- Tools registered in `mcp_server.py`:
  - `web_search(query, max_results)`
  - `scrape_page(url, respect_robots, use_playwright)`
  - `generate_citation(url, title, author, date, style)`
  - `format_output(query, findings, format, style)`
  - `store_memory(text, metadata)`
  - `recall_memory(query, top_k, session_filter)`
- *Architectural Note:* `search_academic_papers` is implemented in `src/tools/search.py` and connected to `ToolClient`, but is not yet decorated with `@mcp.tool()` on `src/mcp_server.py`.

---

## 5. Data Flow & Storage Architecture

### SQLite Relational Schema (`data/research.db`)
Configured with `PRAGMA foreign_keys = ON` in `src/memory/sqlite_store.py`:

```sql
CREATE TABLE IF NOT EXISTS sessions (
    session_id      TEXT PRIMARY KEY,
    user_query      TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    output_format   TEXT CHECK(output_format IN ('brief','comparison','report')),
    status          TEXT CHECK(status IN ('running','completed','failed')) DEFAULT 'running'
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
```

### ChromaDB Vector Schema (`data/chroma`)
- **Collection:** `research_memories`
- **Distance Metric:** Cosine distance (`{"hnsw:space": "cosine"}`)
- **Embeddings Calculation:** Embeddings are generated externally (by `OllamaEmbeddings` or `OpenAIEmbeddings`) and passed directly into Chroma, ensuring Chroma does not download untracked HuggingFace models.
- **Documents:** Synthesized claim strings.
- **Metadata:** Scalar values: `session_id`, `sub_question`, `confidence`, `timestamp`.

---

## 6. External Service Integrations

1. **OpenAlex API (`https://api.openalex.org/works`):**
   - No API key required; passes descriptive User-Agent header with mailto contact.
   - Reconstructs abstracts from `abstract_inverted_index`.
   - Extracts DOIs, open-access PDF URLs, and publication years.
2. **DuckDuckGo Search (`ddgs`):**
   - Free, rate-limit-conscious web retrieval without API tokens.
3. **Ollama HTTP API (`http://localhost:11434`):**
   - `/api/chat`: Runs chat inference with configurable temperature and token clamps.
   - `/api/embeddings`: Generates 768-dim vectors using `nomic-embed-text`.
4. **OpenAI-Compatible Cloud APIs (`src/agent/api_llm.py`):**
   - Direct HTTP client using `httpx`.
   - Supports OpenRouter, OpenAI, Groq, DeepSeek with standard Bearer token authentication.
