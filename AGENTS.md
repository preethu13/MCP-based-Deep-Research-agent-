# AGENTS.md — AI Assistant Guidelines & Engineering Constraints

> **Target Audience:** AI Assistants (Gemini, ChatGPT, Kimi, Claude) and autonomous coding agents working on this repository.  
> **Repository:** MCP-Powered Deep Research Agent  
> **Last Updated:** November 2026  
> **Language & Runtime:** Python 3.11+ / Windows & Linux compatible

---

## 1. Core Operating Principles for AI Assistants

When assisting with this codebase, you must adhere to the following rules:

1. **Verify Implementation Against Reality:**  
   Never assume a planned feature exists until you have inspected the concrete implementation in `src/`. Documentation in `README.md` and `MCP_Deep_Research_Agent_Documentation.md` represents the original vision; always prioritize the live Python code as the source of truth.
2. **Do Not Modify Application Code Unprompted:**  
   Do not refactor, rename, or rewrite existing modules unless explicitly instructed by the user. When asked to inspect or document, generate only documentation.
3. **No Secrets in Repository:**  
   Never hardcode, log, or commit API keys (`OPENAI_API_KEY`, OpenRouter keys, etc.), passwords, or `.env` files. Ensure `.env` is always git-ignored.
4. **Preserve Zero-Exception Tool Guarantees:**  
   All MCP tools in `src/tools/` and `src/mcp_server.py` MUST NEVER raise unhandled exceptions. They must return structured fallback dictionaries or empty lists on failure (Graceful Degradation / Failure Containment).
5. **Maintain In-Process vs. FastMCP Parity:**  
   The agent executes tools in-process via `src/agent/tool_client.py` for speed, while `src/mcp_server.py` exposes them over stdio for external MCP clients (e.g. Claude Desktop). Any new tool added to `src/tools/` must be exposed in both `ToolClient` and `mcp_server.py`.

---

## 2. Codebase Architecture & Key Invariants

### 2.1 The LangGraph Orchestrator
The execution pipeline is an explicit 4-node directed acyclic graph (DAG) defined in `src/agent/graph.py`:

$$\text{START} \longrightarrow \text{planner} \longrightarrow \text{researcher} \longrightarrow \text{synthesizer} \longrightarrow \text{formatter} \longrightarrow \text{END}$$

- **State Container (`ResearchState`):** Defined in `src/agent/state.py` as a `TypedDict`. Nodes receive `state: ResearchState` and return a dictionary of state updates.
- **Dependency Injection (`AgentDeps`):** Node functions are wrapped using `functools.partial(node_fn, deps=deps)`. Never instantiate database connections or HTTP clients inside node functions; access them via `deps.tools`, `deps.llm`, `deps.sqlite`, or `deps.settings`.

### 2.2 Dual LLM Inference Strategy
The agent supports two backends configured via `.env` or `Settings`:
1. **Local Ollama (`src/agent/llm.py`):** Runs local models (`llama3.1:8b`, `nomic-embed-text`) over HTTP via `ollama.Client`.
2. **Cloud API (`src/agent/api_llm.py`):** Direct `httpx` client for OpenAI-compatible endpoints (OpenAI, OpenRouter, Groq) using standard chat completion and embedding payloads.

### 2.3 Search & Relevance Guardrails
- **Stopword Dilution:** Never pass raw conversational sub-questions directly to OpenAlex or DuckDuckGo. Always run them through `clean_search_query()` in `src/tools/search.py`.
- **False-Friend Filtering:** All academic paper candidates must pass through `score_paper_relevance()`. Irrelevant domains (e.g., investing, finance) and acronym collisions (e.g. `Concept-ROT`) must be penalized and discarded.

---

## 3. Coding Conventions & Style Guide

- **Type Hints:** All new functions and methods must have full type annotations (`from __future__ import annotations`, `typing.Any`, `typing.Optional`, etc.).
- **Configuration Management:** All settings must be defined in `src/config.py` using Pydantic `BaseSettings`. Do not read `os.environ` directly in application modules.
- **Path Handling:** Always use `pathlib.Path` instead of string manipulations. Ensure paths work across Windows (backslashes) and Linux/macOS (forward slashes).
- **Concurrency:** Use `ThreadPoolExecutor` for concurrent network requests (e.g. fetching abstracts, scraping pages). Avoid unbounded thread creation; cap workers at 5 to 8.
- **Error Handling:** Log errors using `src.logging_utils.get_logger()`. Return typed fallbacks (e.g., `{"method_used": "failed", "text": "", "error": str(exc)}`).

---

## 4. Verification & Testing Checklist Before Committing

When working on code modifications:
1. **Check Environment & Paths:** Ensure `_PROJECT_ROOT` is handled correctly when imported by CLI (`src/cli/main.py`) or Streamlit (`src/ui/app.py`).
2. **Validate State Immutability:** Nodes should not mutate existing list structures in-place; copy them (`list(state.get("trace", []))`) and return new state dicts.
3. **Verify Database Migrations:** If modifying SQLite schemas in `src/memory/sqlite_store.py`, ensure existing databases in `data/research.db` don't break, or provide safe table creation logic (`CREATE TABLE IF NOT EXISTS`).
4. **Validate UI Theme:** The Streamlit UI uses custom CSS in `src/ui/assets/styles.css` ("The Night Desk" dark theme). Do not use Streamlit default components that clash with custom CSS variables.
