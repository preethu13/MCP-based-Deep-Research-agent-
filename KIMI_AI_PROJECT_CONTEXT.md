# DEEP RESEARCH AGENT — COMPLETE PROJECT DOSSIER & CONTEXT FOR AI (KIMI / CHATGPT / CLAUDE)

> **Purpose of this Document:**  
> Feed this entire document to Kimi AI (or any conversational AI) as initial context. It provides a complete, 360-degree technical briefing of the codebase, system design, architectural trade-offs, database schemas, and current state so the AI can immediately converse with you as an expert co-pilot, review code, propose improvements, and help make informed engineering decisions.

---

## 1. System Prompt for Kimi AI (Role Definition)

*When pasting this to Kimi AI, prepend this block:*

```text
You are an expert Principal AI Systems Architect and Staff Software Engineer acting as a technical co-pilot for the "MCP-Powered Deep Research Agent" project.
Below is the full technical briefing of the project, including its philosophy, code structure, data flow, recent bug fixes, and active challenges.
Read the entire specification carefully. Once loaded, you are ready to:
1. Answer architectural and implementation questions about any module in the system.
2. Propose code improvements, refactoring, and feature additions that respect the existing architecture.
3. Help diagnose edge cases (e.g., retrieval quality, latency, token limits, memory management).
4. Guide roadmap decisions (e.g., rerankers, multi-hop search, PDF ingestion, agentic reflection).
```

---

## 2. Project Vision & Executive Summary

The **MCP-Powered Deep Research Agent** is an autonomous scientific research analyst. Unlike standard conversational LLMs that hallucinate facts or invent fake citations, this system operates deterministically:
1. **Decomposes** an ambiguous research query into focused sub-questions.
2. **Checks local long-term memory** first to reuse verified past findings (saving time and API calls).
3. **Retrieves peer-reviewed literature** via scientific indexes (OpenAlex API across 250M+ scientific papers) and live web sources (DuckDuckGo).
4. **Applies strict relevance filtering** to eliminate false-friend keyword matches.
5. **Extracts verified abstracts & text**, bypassing unnecessary web scraping when official author abstracts are available.
6. **Synthesizes grounded claims** strictly from gathered evidence, attributing every claim to its source.
7. **Compiles a publication-ready dossier** complete with clickable DOI/PDF links, structured metadata, and formal APA-7 / MLA-9 bibliographies.

### Core Architectural Pillars
- **Zero Hallucinated Citations:** Every claim must be tied to a database-backed citation with a live DOI, landing page, or scraped URL.
- **Dual Inference Engine:** Runs either 100% locally with **Ollama** (`llama3.1:8b`, `nomic-embed-text`) for $0 privacy-first inference, OR connects to **Cloud APIs** (OpenAI, OpenRouter, DeepSeek, Anthropic) via a unified client (`src/agent/api_llm.py`).
- **Standardized Tool Protocol (MCP):** Search, scraping, citation generation, formatting, and memory are implemented as discrete tools compatible with Anthropic's **Model Context Protocol (FastMCP)**.
- **Graph Orchestration:** A deterministic, cyclic/stateful workflow orchestrated by **LangGraph**.

---

## 3. Technology Stack

| Layer | Technology | Role in System |
| :--- | :--- | :--- |
| **Language** | Python 3.11+ | Core runtime across all packages |
| **Orchestration** | `langgraph` (v0.2+) | State-machine workflow engine (`ResearchState`) |
| **Tool Protocol** | `fastmcp` / MCP SDK | Decoupled tool server & client interfaces |
| **Relational Store** | SQLite3 (`data/research.db`) | Sessions, research findings, citations, query history |
| **Vector Memory** | ChromaDB (`data/chroma`) | Semantic embedding store for cross-session knowledge recall |
| **Academic Retrieval** | OpenAlex REST API | 250M+ scientific literature records, DOIs, open-access PDFs, abstracts |
| **Web Search** | `duckduckgo-search` (`ddgs`) | Real-time web retrieval without requiring search API keys |
| **Web Scraping** | `httpx` + `beautifulsoup4` | Async HTML fetching, DOM parsing, and clean markdown extraction |
| **Local LLM** | Ollama | Local inference for chat (`llama3.1:8b`) and embeddings (`nomic-embed-text`) |
| **Cloud LLM** | Custom OpenAI-compatible HTTP client | Fast cloud inference via OpenRouter, OpenAI, Groq, etc. |
| **User Interface** | Streamlit (`src/ui/app.py`) | Interactive dashboard with live research trace, logs, and citations |
| **CLI Interface** | `typer` + `rich` | Terminal command-line interface with formatted progress trees |

---

## 4. End-to-End System Workflow (LangGraph State Machine)

The research pipeline is driven by an explicit 4-node LangGraph directed acyclic graph (DAG):

```
[START]
   │
   ▼
[1. PLANNER] ──────────► Decomposes user query into 2-3 targeted sub-questions
   │
   ▼
[2. RESEARCHER] ───────► Recall memory -> Query OpenAlex & Web -> Relevance Filter -> Scrape/Extract
   │
   ▼
[3. SYNTHESIZER] ──────► Grounded batch synthesis -> Persist findings/citations to SQLite & ChromaDB
   │
   ▼
[4. FORMATTER] ────────► Compiles final Markdown dossier, tables, and formal APA/MLA bibliography
   │
   ▼
 [END]
```

### Detailed Node Breakdown

#### 1. Planner Node (`src/agent/nodes/planner.py`)
- Receives user query (e.g., `"context rot in llm"`).
- Directs the LLM to return a strict JSON array of 2 to 3 concise, highly focused academic sub-questions.
- Sub-questions are instructed to preserve the core subject topic keywords so scientific search engines don't lose context.
- *Fallback:* Heuristic regex splitter if LLM fails or returns unparseable text.

#### 2. Researcher Node (`src/agent/nodes/researcher.py`)
For each sub-question:
1. **Recall-Before-Search:** Queries ChromaDB for past session findings. If $\ge 2$ strong matches exist, it short-circuits and skips external search.
2. **Query Keyword Sanitization:** Uses `clean_search_query()` to strip question stopwords (`"What are"`, `"mitigation strategies"`) down to dense search terms anchored to the primary topic (`"context rot llm architectures"`).
3. **Academic Paper Search (OpenAlex):** Queries OpenAlex for peer-reviewed papers. OpenAlex provides structured titles, publication years, author lists, venues, DOIs, open-access PDF links, and inverted-index abstracts.
4. **Web Search (DuckDuckGo):** Queries DDG for web articles, technical blogs, and documentation.
5. **Relevance Scoring & Anti-Collision Filter (`score_paper_relevance`):**
   - Scores candidates based on title phrase matches and abstract keyword density.
   - Applies penalties to off-topic acronym collisions (e.g. `Concept-ROT` trojans) and domain mismatches (e.g. stock investing).
   - Drops candidates with negative scores.
6. **Abstract Fast-Path:** If an authentic paper abstract was returned by OpenAlex, network scraping is skipped entirely (saving 10–30 seconds per query). Otherwise, `scrape_page()` fetches and cleans the DOM using `httpx` + `BeautifulSoup`.

#### 3. Synthesizer Node (`src/agent/nodes/synthesizer.py`)
- Receives the gathered contexts per sub-question.
- Uses **Batch Synthesis** (`_batch_synthesize_claims`): sends all sub-questions and contexts in a single coordinated LLM pass rather than 3 sequential calls.
- Constrains the LLM to generate 2–4 concise, factual sentences strictly supported by the sources.
- **Storage:**
  - Persists each finding and its linked citations into SQLite (`findings` and `citations` tables).
  - Embeds each claim into ChromaDB (`research_memory` collection) for future recall.

#### 4. Formatter Node (`src/agent/nodes/formatter.py`)
- Resolves citations to either APA-7th or MLA-9th format.
- Automatically generates three output sections:
  1. **Executive Dossier / Key Findings:** Numbered, citation-anchored claims.
  2. **Peer-Reviewed Papers & Literature:** Clickable DOIs, direct open-access PDF links, publication years, and author rosters.
  3. **Formal References Bibliography:** Alphabetically sorted formal citations.

---

## 5. Codebase Directory Structure

```text
MCP-based-Deep-Research-agent-/
├── .env                          # Local environment variables (Ollama host, API keys, paths)
├── .env.example                  # Template configuration
├── requirements.txt              # Production Python dependencies
├── SYSTEM_ARCHITECTURE.md        # Comprehensive system design document
├── KIMI_AI_PROJECT_CONTEXT.md    # THIS FILE (Context dossier for AI models)
│
├── data/
│   ├── research.db               # SQLite relational database (sessions, findings, citations)
│   └── chroma/                   # ChromaDB persistent vector database directory
│
└── src/
    ├── config.py                 # Pydantic Settings (paths, models, timeouts, thresholds)
    │
    ├── agent/
    │   ├── state.py              # ResearchState TypedDict and AgentDeps container
    │   ├── graph.py              # LangGraph StateGraph builder and ResearchAgent class
    │   ├── llm.py                # Local OllamaLLM implementation (chat + JSON mode)
    │   ├── api_llm.py            # Cloud LLM client (OpenAI / OpenRouter / compatible APIs)
    │   ├── tool_client.py        # In-process bridge executing tools for agent nodes
    │   │
    │   └── nodes/
    │       ├── planner.py        # Decomposes root query into sub-questions
    │       ├── researcher.py     # Recall, academic search, relevance ranking, scraping
    │       ├── synthesizer.py    # Grounded batch synthesis and persistence
    │       └── formatter.py      # Markdown formatting, APA/MLA references, paper lists
    │
    ├── tools/
    │   ├── search.py             # OpenAlex academic API + DuckDuckGo search + query sanitizer
    │   ├── scraper.py            # HTTP scraping, robots.txt verification, text extraction
    │   ├── citation.py           # APA-7 / MLA-9 deterministic citation generator
    │   ├── formatter.py          # Output layout compiler (brief, comparison table, report)
    │   ├── sqlite_store.py       # SQLite CRUD operations for sessions, findings, citations
    │   ├── chroma_store.py       # ChromaDB vector wrapper (recall_memory, store_memory)
    │   └── server.py             # FastMCP server exposing tools via Model Context Protocol
    │
    └── ui/
        └── app.py                # Streamlit Web UI ("The Night Desk" dark theme)
```

---

## 6. Database Schemas

### SQLite Schema (`data/research.db`)

```sql
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_query TEXT NOT NULL,
    output_format TEXT DEFAULT 'brief',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'completed'
);

CREATE TABLE IF NOT EXISTS findings (
    finding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    sub_question TEXT,
    claim_text TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS citations (
    citation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id INTEGER REFERENCES findings(finding_id),
    url TEXT NOT NULL,
    title TEXT,
    author TEXT,
    published_date TEXT,
    citation_text TEXT
);
```

### ChromaDB Vector Schema (`data/chroma`)
- **Collection Name:** `research_memory`
- **Embedding Dimensions:** 768 (when using `nomic-embed-text`) or 1536 (when using `text-embedding-3-small`)
- **Document Text:** The synthesized claim string.
- **Metadata:**
  ```json
  {
    "session_id": "sess_46671ed142be",
    "sub_question": "What are the theoretical frameworks explaining context rot in LLMs?",
    "confidence": 1.0,
    "timestamp": 1732347839.2
  }
  ```

---

## 7. Key Problems Solved & Critical Insights

### Problem 1: Retrieval Failure on Specific Academic Concepts ("Context Rot")
- **Symptom:** When searching `"context rot in llm"`, OpenAlex returned papers on *“Managing LLM Bias in Investing”* and *“Concept-ROT: Poisoning Concepts with Model Editing”*.
- **Root Cause:**
  1. The Planner generated long conversational sentences: `"What are the potential consequences and mitigation strategies for context rot in real-world LLM applications?"`.
  2. OpenAlex uses BM25 full-text search. The words `"mitigation"`, `"strategies"`, and `"applications"` diluted the query and matched financial bias mitigation papers.
  3. The word `"rot"` matched the adversarial security paper with acronym `Concept-ROT`.
  4. There was no relevance filter: the agent took the first $N$ results blindly.
- **Resolution:**
  - Added `clean_search_query()` to distill conversational questions down to essential keywords anchored by the primary query.
  - Implemented `score_paper_relevance()`: checks title/abstract concept density, penalizes false-friend acronyms, penalizes off-topic domains (finance, real estate), and drops candidates with negative scores.

### Problem 2: Slow Response Times (200s+ down to ~15-25s)
- **Root Cause:** Scraping full HTML pages across 9 URLs sequentially, followed by sequential LLM synthesis calls with unbounded token generation.
- **Resolution:**
  - **Abstract Fast-Path:** OpenAlex returns reconstructed abstracts. If an abstract exists, network scraping is bypassed entirely.
  - **Batch Synthesis:** Combined 3 separate synthesis LLM calls into a single structured JSON batch call.
  - **Token Clamping:** Added `max_tokens` limits (90 for planning, 300 for synthesis) to eliminate rambling token generation.

---

## 8. Open Discussion Topics to Explore with Kimi AI

When you chat with Kimi AI, here are high-impact architectural decisions and feature enhancements you can ask it to help design:

1. **Multi-Hop / Iterative Agentic Search:**
   - *Current state:* Single-pass (Plan $\rightarrow$ Search $\rightarrow$ Synthesize).
   - *Topic:* How to implement an evaluator loop where the agent assesses if the retrieved papers sufficiently answer the query, and if not, reformulates a new query (Plan $\rightarrow$ Search $\rightarrow$ Evaluate $\rightarrow$ [Refine Search] $\rightarrow$ Synthesize).

2. **Full-Text PDF Ingestion vs. Abstract-Only RAG:**
   - *Current state:* Uses OpenAlex paper abstracts and web snippets.
   - *Topic:* How to cleanly integrate a lightweight, asynchronous PDF parser (`pypdf` or `pymupdf`) to pull full methodology and results sections from open-access PDFs when abstracts are too brief.

3. **Neural Re-ranking (Cross-Encoders):**
   - *Current state:* Lightweight lexical/heuristic scoring in `score_paper_relevance()`.
   - *Topic:* Should we plug in a small local cross-encoder (e.g., `bge-reranker-small` or `flashrank`) to re-rank search results with zero external API calls?

4. **Multi-Provider LLM Fallbacks:**
   - *Current state:* Either Ollama or OpenRouter/OpenAI based on `.env`.
   - *Topic:* Implementing automatic fallback (if local Ollama is offline or times out, seamlessly route to cloud API; if cloud API hits rate limit, fall back to local Ollama).

5. **Export Formats & User Experience:**
   - *Topic:* Adding one-click export to PDF (via `weasyprint` or markdown-to-pdf), Word DOCX, and BibTeX format for academic researchers.

---

## 9. Checklist: What Other Files / Sources to Give to Kimi AI

If you are uploading files or sharing code snippets with Kimi AI in your chat, provide these key files in order of importance:

| Priority | File Path | Why Kimi AI Needs It |
| :---: | :--- | :--- |
| **1** | `src/agent/graph.py` | Defines the LangGraph state machine, node wiring, and `ResearchAgent` API. |
| **2** | `src/agent/nodes/researcher.py` | Contains the retrieval logic, recall-before-search, and relevance scoring loop. |
| **3** | `src/tools/search.py` | Contains OpenAlex integration, `clean_search_query()`, and `score_paper_relevance()`. |
| **4** | `src/agent/nodes/synthesizer.py` | Contains batch synthesis prompts, database persistence, and grounding rules. |
| **5** | `src/agent/api_llm.py` | Contains the OpenAI/OpenRouter HTTP client for cloud LLM inference. |
| **6** | `src/config.py` | Contains Pydantic settings, model parameters, timeout configs, and directory paths. |
| **7** | `src/ui/app.py` | The Streamlit dashboard frontend (if discussing UI features or UX changes). |
| **8** | `requirements.txt` | Shows exact library versions installed in your environment. |

---

## 10. Quick Start Commands (For Testing & Running)

```bash
# 1. Activate Virtual Environment
.venv\Scripts\activate

# 2. Run the Streamlit Dashboard
streamlit run src/ui/app.py

# 3. Run a direct CLI research query
python -m src.agent.cli "context rot in llm" --format brief --style apa

# 4. Run tests
pytest tests/
```
