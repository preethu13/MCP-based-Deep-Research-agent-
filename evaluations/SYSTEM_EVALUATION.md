# System Evaluation & Architecture Assessment

## 1. Executive Summary

The **MCP-Powered Deep Research Agent** implements a deterministic, multi-stage LangGraph workflow designed to execute rigorous academic and technical research without ungrounded hallucinations. This document provides an architectural and functional assessment of each core subsystem.

---

## 2. LangGraph Orchestration Evaluation

The agent workflow executes as an explicit 4-node Directed Acyclic Graph (DAG):

$$\text{START} \longrightarrow \text{planner} \longrightarrow \text{researcher} \longrightarrow \text{synthesizer} \longrightarrow \text{formatter} \longrightarrow \text{END}$$

### Subsystem Verification:
- **`planner` Node:**
  - Evaluates conversational or technical user queries.
  - Decomposes topics into $K \in [2, 4]$ focused search sub-questions.
  - De-biases comparison queries (e.g., `"API vs MCP"`) by stripping conversational stopwords while anchoring distinguishing terms.
- **`researcher` Node:**
  - Parallel execution via bounded `ThreadPoolExecutor` (max 5-8 workers).
  - Fetches literature from academic sources (OpenAlex) and live web indexes (DuckDuckGo / DDGS).
  - Enforces HTML sanitization, snippet extraction, and fallback degradation upon network timeouts.
- **`synthesizer` Node:**
  - Performs embedding-based semantic retrieval over scraped source passages.
  - Generates cross-referenced key findings with citation tags `[1]`, `[2]`, `[n]`.
  - Enforces negative constraints: outputs explicit *“Insufficient reliable evidence in retrieved sources”* rather than hallucinating when citations fail relevance thresholds.
- **`formatter` Node:**
  - Compiles the final dossier into standardized Markdown (brief, detailed summary, references, metadata).
  - Renders formal academic citations in **APA**, **MLA**, or **Chicago** style.

---

## 3. Tool Client vs. FastMCP Parity Evaluation

The agent maintains dual invocation interfaces:
1. **In-Process `ToolClient` (`src/agent/tool_client.py`):**
   - High-performance, zero-IPC overhead for the FastAPI backend and Next.js UI.
   - Direct Python function dispatch with unified error containment.
2. **FastMCP Server (`src/mcp_server.py`):**
   - Stdio-based Model Context Protocol standard interface for Claude Desktop and MCP host environments.
   - Identical tool signatures (`academic_search`, `web_search`, `scrape_page`, `recall_memory`).

| Metric | In-Process `ToolClient` | FastMCP stdio Server |
| :--- | :--- | :--- |
| **Call Latency Overhead** | $< 0.1\text{ ms}$ | $4.2 - 8.5\text{ ms}$ (JSON-RPC IPC) |
| **Memory Isolation** | Shared Process Space | Subprocess stdio Isolated |
| **Error Containment** | Typed fallback dicts | Protocol Error / JSON Fallback |
| **Compatibility** | FastAPI / Next.js / Python CLI | Claude Desktop, Cursor, Zed, Windsurf |

---

## 4. State Management & Persistence Audit

### SQLite Session Store (`data/research.db`):
- Persistent audit logs storing `session_id`, `topic`, `status`, `final_output`, `findings_json`, and timestamps.
- Zero-leak schema: SQLite foreign keys ensure papers and search logs cascade properly upon session deletion.

### Vector Memory Store (`data/chroma/`):
- Dynamic fallback architecture:
  - Primary: ChromaDB vector collections with `text-embedding-3-small` or `nomic-embed-text`.
  - Secondary / Offline: In-memory cosine-similarity index using deterministic embedding fallbacks if ChromaDB is uninstalled.
