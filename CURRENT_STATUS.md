# CURRENT_STATUS.md — Implementation Health & Roadmap

> **Repository:** MCP-Powered Deep Research Agent  
> **Last Verified:** November 23, 2026  
> **Current Stability:** Working Prototype / Functional MVP  

---

## 1. Feature Completion Matrix

| Feature / Capability | Status | Implementation Location | Notes |
| :--- | :---: | :--- | :--- |
| **Academic Paper Search** | **Completed** | `src/tools/search.py` | OpenAlex API integration with DOIs, PDFs, and abstracts. |
| **Search Query Sanitization** | **Completed** | `src/tools/search.py` | Strips question noise; anchors queries to core topics. |
| **Relevance Scoring & Filtering** | **Completed** | `src/tools/search.py` | Heuristic scoring drops off-topic false friends and acronym collisions. |
| **Abstract Fast-Path** | **Completed** | `src/agent/nodes/researcher.py` | Instant abstract extraction without HTML scraping. |
| **Batch Synthesis** | **Completed** | `src/agent/nodes/synthesizer.py` | Generates all findings in one LLM call (~10-15s total run). |
| **Inference & Embeddings Engine** | **Completed** | `src/agent/api_llm.py`, `src/agent/llm.py` | Primary OpenRouter/OpenAI API (`gpt-4o-mini`, `text-embedding-3-small`) + optional local Ollama (`llama3.1:8b`, `nomic-embed-text`). |
| **Multi-Tier & Instant Query Cache** | **Completed** | `src/memory/cache.py`, `src/memory/sqlite_store.py` | In-memory LRU + SQLite cache; instant (0.05s) response for repeated queries. |
| **Relational Session Store** | **Completed** | `src/memory/sqlite_store.py` | SQLite schema with foreign keys, cascading deletes, and session result caching. |
| **Vector Memory Recall** | **Completed** | `src/memory/vector_store.py` | ChromaDB vector recall with recall-before-search short-circuit. |
| **APA 7th & MLA 9th Formatting** | **Completed** | `src/tools/citation.py`, `src/tools/formatter.py` | Deterministic citation generator with structured paper roster. |
| **Streamlit Web UI** | **Completed** | `src/ui/app.py` | "The Night Desk" dark theme with live SSE-like execution trace. |
| **Typer CLI Interface** | **Completed** | `src/cli/main.py` | Command-line tool with rich terminal progress trees. |
| **FastMCP Academic Tool Exposure** | **Completed** | `src/mcp_server.py` | Decorated with `@mcp.tool()` `search_academic_papers` for external MCP parity. |
| **Playwright JS Scraping** | **Partially Implemented** | `src/tools/scrape.py` | Code exists, but Playwright browser binaries must be manually installed; falls back to static `httpx`. |
| **Multi-Hop / Iterative Search** | **Not Implemented** | Planned | Pipeline is single-pass (Plan -> Search -> Synthesize); no evaluation loop to re-query if results are incomplete. |
| **Full PDF Parsing** | **Not Implemented** | Planned | Only paper abstracts and web pages are parsed; PDF download/text extraction is not implemented. |
| **Interactive Post-Research Q&A** | **Not Implemented** | Planned (`paln.md`) | User cannot yet ask interactive follow-up questions on retrieved papers. |
| **React/TypeScript Frontend** | **Not Implemented** | Planned (`paln.md`) | Streamlit is the only web UI currently available. |
| **Production Docker Deployment** | **Not Implemented** | Planned | No `Dockerfile` or `docker-compose.yml` present in repository. |

---

## 2. Current Technical Limitations & Known Issues

1. **Pytest in `requirements-dev.txt`:**  
   `pytest` is located in `requirements-dev.txt`. Users who run `pip install -r requirements.txt` cannot run the test suite without installing developer dependencies.
2. **Windows Sandbox Network Restrictions:**  
   On Windows environments with secure sandbox policies, outbound socket connections for DuckDuckGo and OpenAlex can be blocked unless bypassed.
4. **Streamlit Global Secrets Permission:**  
   Streamlit searches for `~/.streamlit/secrets.toml`. If sandbox permissions restrict user home directory access, Streamlit raises `PermissionError` unless granted appropriate filesystem access.
5. **OpenAlex Abstract Formatting:**  
   Some older papers in OpenAlex lack an inverted index abstract (`abstract_inverted_index`), requiring fallback to title snippets or web scraping.

---

## 3. Immediate Next Development Tasks (From `paln.md` and Active State)

- [ ] **Task 1: Expose Academic Search on FastMCP Server:** Add `@mcp.tool()` wrapper for `search_academic_papers` in `src/mcp_server.py`.
- [ ] **Task 2: Interactive Follow-Up Chat on Papers:** Allow users in the Streamlit UI to ask follow-up questions on retrieved papers without restarting a full research run.
- [ ] **Task 3: Full-Text PDF Extractor:** Integrate a lightweight PDF parser (`pypdf` or `pymupdf`) to ingest open-access PDFs when paper abstracts are insufficient.
- [ ] **Task 4: Add Neural Reranker Option:** Evaluate integrating `flashrank` or `bge-reranker-small` as an optional local neural reranking step.
- [ ] **Task 5: Export Functionality:** Add one-click export for PDF (via markdown-to-pdf) and BibTeX reference formats in the UI and CLI.
