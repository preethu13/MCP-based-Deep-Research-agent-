# CHANGELOG.md — Deep Research Agent Change History

> **Repository:** MCP-Powered Deep Research Agent  
> **Format:** Based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  

---

## [Unreleased / Current Active Iteration] — November 2026

### Added
- **Academic Literature Retrieval (`src/tools/search.py`):**
  - Integrated OpenAlex API (`search_academic_papers`) to query 250M+ scientific records with real DOIs, verified abstracts, publication years, author rosters, and open-access PDF URLs.
- **Academic Dossier Layout (`src/tools/formatter.py`):**
  - Added dedicated **"Research Papers & Literature"** section rendering structured paper titles, publication venues, DOIs, and direct open-access PDF links alongside formal APA/MLA citations.
- **Cloud API Inference Engine (`src/agent/api_llm.py`):**
  - Created standalone `OpenAILLM` and `OpenAIEmbeddings` clients using `httpx` to support OpenAI-compatible cloud providers (OpenRouter, OpenAI, Groq, DeepSeek) without installing heavy vendor SDKs.
- **Search Query Sanitization (`src/tools/search.py`):**
  - Added `clean_search_query()` to strip conversational question stopwords (`"What are"`, `"How do"`, `"mitigation strategies"`) while anchoring queries to core technical keywords.
- **Relevance Scoring & Anti-Collision Filter (`src/tools/search.py`):**
  - Added `score_paper_relevance()`: evaluates title/abstract keyword density, penalizes off-topic acronym collisions (e.g. `Concept-ROT` trojans), drops domain mismatches (e.g. stock investing), and filters out candidates scoring $<0.5$.
- **Batch Synthesis (`src/agent/nodes/synthesizer.py`):**
  - Implemented `_batch_synthesize_claims()`: bundles all sub-questions and contexts into a single structured JSON LLM call, reducing runtime from >200s to ~15-25s.
- **Abstract Fast-Path (`src/agent/nodes/researcher.py`):**
  - Papers with authentic author abstracts bypass web scraping entirely, saving network bandwidth and execution latency.
- **Streamlit Path Resolution (`src/ui/app.py`):**
  - Added dynamic project root resolution to `sys.path` so Streamlit can be launched directly via `streamlit run src/ui/app.py`.

### Fixed
- **Off-Topic False Friend Retrieval:** Fixed bug where queries like `"context rot in llm"` returned unrelated papers on trojan model editing and financial bias mitigation due to raw sentence token dilution.
- **Token Runaway & Timeout:** Clamped LLM generation tokens (`max_tokens=90` in planner, `max_tokens=300` in synthesizer) to prevent open-ended inference loops.

---

## [1.0.0] — 2026-08-29 (Commit: `58e820d`)

### Added
- **LangGraph State Machine (`src/agent/graph.py`):**
  - Implemented 4-node research pipeline: `planner -> researcher -> synthesizer -> formatter`.
  - Defined `ResearchState` and telemetry event streaming.
- **FastMCP Tool Server (`src/mcp_server.py`):**
  - Implemented MCP tools: `web_search`, `scrape_page`, `generate_citation`, `format_output`, `store_memory`, `recall_memory`.
- **Local Ollama Integration (`src/agent/llm.py`, `src/memory/embeddings.py`):**
  - Added `OllamaLLM` for chat (`llama3.1:8b`) and `OllamaEmbeddings` for vector embeddings (`nomic-embed-text`).
- **Persistent Dual Memory Layer (`src/memory/`):**
  - SQLite schema (`sessions`, `findings`, `citations`, `memories`) in `data/research.db`.
  - ChromaDB vector store (`research_memories` collection) in `data/chroma`.
- **Web Scraping Subsystem (`src/tools/scrape.py`):**
  - Static HTML fetching with `httpx` + `BeautifulSoup4` with robots.txt validation.
  - Headless browser fallback via Playwright for JavaScript-heavy web pages.
- **User Interfaces (`src/cli/`, `src/ui/`):**
  - Typer CLI with `ask`, `sessions`, `doctor` commands.
  - Streamlit web interface ("The Night Desk" dark theme) with live execution logs.
- **Automated Test Suite (`tests/`):**
  - Unit tests for citation, scrape, search, formatter, SQLite, and Chroma stores.
  - Integration tests for agent graph and MCP server.
