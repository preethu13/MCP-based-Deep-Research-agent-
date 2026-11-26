# PROJECT_CONTEXT.md — Deep Research Agent Implementation Overview

> **Repository:** MCP-Powered Deep Research Agent  
> **Documentation Version:** 1.0 (Live Implementation State)  
> **Status:** Functional Prototype with Dual Local/Cloud Inference & Academic Literature Integration  

---

## 1. Project Purpose & Objectives

The **MCP-Powered Deep Research Agent** is an autonomous scientific and web research system designed to eliminate AI hallucination in research dossiers. Instead of answering queries from static weights, the agent acts as a diligent research analyst that:

1. **Decomposes** high-level or ambiguous research questions into focused academic sub-questions.
2. **Prioritizes Historical Memory:** Checks local vector storage (ChromaDB) before hitting the network, avoiding duplicate research.
3. **Retrieves Real Academic Literature:** Connects to the **OpenAlex API** (250M+ scientific publications) and DuckDuckGo to obtain peer-reviewed papers with real DOIs, verified abstracts, author lists, and open-access PDF links.
4. **Filters False Friends:** Sanitizes queries to prevent keyword dilution and uses lexical relevance scoring to discard off-topic search results.
5. **Extracts Evidence Efficiently:** Uses an abstract fast-path (bypassing scraping when publisher abstracts exist) or scrapes web pages with BeautifulSoup/Playwright.
6. **Synthesizes Grounded Claims:** Uses batch LLM generation to produce factual summaries tied to exact source citations.
7. **Compiles Publication-Ready Dossiers:** Formats output into Briefs, Comparison Tables, or Detailed Reports with formal APA-7th or MLA-9th bibliographies.

---

## 2. Complete Technology Stack

| Component | Library / Technology | Version / Spec | Purpose in Implementation |
| :--- | :--- | :--- | :--- |
| **Language** | Python | `>=3.11` | Primary development runtime |
| **Agent Orchestrator** | `langgraph` | `>=0.2.28` | State machine DAG connecting Planner, Researcher, Synthesizer, Formatter |
| **Tool Protocol** | `fastmcp` | `>=2.3.0` | Exposes research tools over Model Context Protocol |
| **Primary Cloud LLM & Embeddings** | `httpx` (Custom `OpenAILLM`) | `>=0.27.0` | Primary cloud inference via OpenRouter / OpenAI endpoints (`gpt-4o-mini`, `text-embedding-3-small`) |
| **Optional Local LLM Engine** | `ollama` (Optional) | `>=0.3.3` | Optional local chat (`llama3.1:8b`) and embeddings (`nomic-embed-text`) |
| **Relational Database & Cache** | `sqlite3` (`data/research.db`) | Standard Library | Stores sessions, findings, citations, vector mappings, and completed research cache |
| **Vector Database** | `chromadb` (`data/chroma`) | `>=0.5.5` | Persistent vector store with cosine distance for semantic recall |
| **Academic Retrieval** | OpenAlex REST API | `api.openalex.org` | 250M+ peer-reviewed papers, open-access PDFs, abstracts |
| **Web Search** | `ddgs` (`duckduckgo-search`) | `>=7.0.0` | Real-time web search without API keys |
| **HTML Scraping** | `httpx` + `beautifulsoup4` | `>=4.12.0` | HTTP GET, robots.txt parsing, DOM cleanup |
| **Headless Browser** | `playwright` | `>=1.44.0` | Optional fallback for JavaScript-rendered web pages |
| **Configuration** | `pydantic` + `python-dotenv` | `>=2.7.0` | Type-safe environment settings in `src/config.py` |
| **CLI Framework** | `typer` + `rich` | `>=0.12.0` | Terminal UI with live trees and status logs |
| **Web Interface** | `streamlit` | `>=1.36.0` | Browser dashboard with live SSE-like execution trace |

---

## 3. Features & Current Capabilities

### Implemented & Verified Capabilities
- **Academic Paper Ingestion:** Direct OpenAlex integration returning paper title, publication year, authors, publisher/venue, landing URL, direct PDF URL, and reconstructed abstracts.
- **Query Sanitization:** `clean_search_query()` strips question noise words (`"What are"`, `"How do"`) while preserving core technical topics.
- **Relevance Scoring & Anti-Collision:** `score_paper_relevance()` evaluates title/abstract keyword overlap, penalizing off-topic acronym collisions (e.g. `Concept-ROT`) and domain mismatches (e.g. stock investing).
- **Abstract Fast-Path:** Instant retrieval bypassing HTTP scraping when publisher abstracts are available from OpenAlex.
- **Batch Synthesis:** Single coordinated LLM pass in `src/agent/nodes/synthesizer.py` generating all findings simultaneously, cutting runtimes to ~10-15s.
- **Instant Research Caching:** Completed research sessions (findings, claims, bibliography) are cached in SQLite for immediate (0.05s) response on repeated or related queries.
- **Primary OpenRouter Inference & Optional Local Ollama:**
  - OpenRouter / Cloud API (`OpenAILLM` + `OpenAIEmbeddings`) as the primary inference engine using `gpt-4o-mini` and `text-embedding-3-small`.
  - Local Ollama (`OllamaLLM` + `OllamaEmbeddings`) as an optional local offline alternative.
- **Structured Persistent Memory:**
  - Relational SQLite tables for sessions, findings, and citations (`data/research.db`).
  - Vector embeddings in ChromaDB (`data/chroma`) with recall-before-search short-circuiting.
- **Academic Citation Formatting:** Formal APA 7th and MLA 9th bibliographies, plus a dedicated "Research Papers & Literature" section with direct DOI/PDF links.
- **Streamlit Web UI ("The Night Desk"):** Dark-themed dashboard displaying live agent execution traces, research briefs, tables, and memory search.
- **CLI Commands:** `research ask`, `research sessions list`, `research sessions recall`, `research doctor`.

---

## 4. Existing Implementation Details

### File Structure & Module Responsibilities

```text
src/
├── config.py                 # Pydantic Settings: model names, paths, timeouts, API keys
├── logging_utils.py          # Structured logging configuration
├── mcp_server.py             # FastMCP tool server exposing tools to external MCP hosts
│
├── agent/
│   ├── graph.py              # LangGraph compilation, StateGraph wiring, ResearchAgent class
│   ├── state.py              # ResearchState TypedDict, AgentDeps dataclass, trace telemetry
│   ├── llm.py                # OllamaLLM implementation (chat + JSON mode)
│   ├── api_llm.py            # OpenAILLM & OpenAIEmbeddings implementation via httpx
│   ├── tool_client.py        # In-process tool bridge with fallback guarantees
│   ├── demo.py               # DemoLLM / offline mock model for UI testing
│   └── nodes/
│       ├── planner.py        # Query decomposition into focused sub-questions
│       ├── researcher.py     # Memory recall, academic search, relevance ranking, scraping
│       ├── synthesizer.py    # Grounded batch synthesis and database persistence
│       └── formatter.py      # Final markdown assembly, tables, APA/MLA formatting
│
├── tools/
│   ├── search.py             # OpenAlex academic index + DuckDuckGo search + relevance scoring
│   ├── scrape.py             # httpx + BeautifulSoup scraper with Playwright fallback
│   ├── citation.py           # APA-7 and MLA-9 deterministic citation generator
│   ├── formatter.py          # Formatter layouts (brief, comparison, report) & paper listings
│   ├── memory.py             # High-level memory wrapper (store_memory, recall_memory)
│   └── models.py             # Pydantic data models for tools
│
├── memory/
│   ├── sqlite_store.py       # SQLite connection manager, schema initialization, and CRUD
│   ├── vector_store.py       # ChromaDB wrapper with cosine similarity and metadata sanitation
│   └── embeddings.py         # OllamaEmbeddings and HashingEmbeddings (fallback)
│
├── cli/
│   └── main.py               # Typer CLI application
│
└── ui/
    ├── app.py                # Streamlit web application
    └── assets/styles.css     # "The Night Desk" custom dark theme styling
```
