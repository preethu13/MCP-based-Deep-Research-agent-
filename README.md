# 🌙 MCP-Powered Deep Research Agent

> **A $0-cost autonomous research analyst running entirely on your machine.**  
> Plans questions, reads the open web, cites every claim, and remembers what you asked before.

[![CI](https://github.com/yourusername/mcp-deep-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/mcp-deep-research-agent/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Cost: $0](https://img.shields.io/badge/cost-%240.00-brightgreen.svg)](#cost)

---

## What it does

The agent takes an ambiguous research question, breaks it into sub-questions, searches DuckDuckGo, reads multiple web pages, cross-checks claims, **cites every fact**, stores findings in persistent vector + SQLite memory for future sessions, and delivers the output in three formats:

| Format | Best for |
|--------|----------|
| **Brief** | Quick 1-page summary with bullet points |
| **Comparison** | Side-by-side Markdown table (great for "X vs Y vs Z") |
| **Report** | Long-form insight report with executive summary |

---

## Architecture

```
User (CLI / Streamlit UI)
        |
        v
+-------------------------------------+
|         LangGraph Orchestrator       |
|  Planner -> Researcher -> Synthesizer|
|           -> Formatter               |
+----------------+--------------------+
                 |  in-process tool calls
                 v
+-------------------------------------+
|           FastMCP Server            |
|  web_search  search_academic_papers |
|  scrape_page generate_citation      |
|  format_output store_memory recall  |
+----------+---------------------------+
           |                     |
    +------+              +------+
    v                     v
DuckDuckGo +          SQLite + ChromaDB
OpenAlex +            (persistent memory &
BeautifulSoup         instant query cache)
           |
           v
    Primary: OpenRouter / OpenAI API (gpt-4o-mini, text-embedding-3-small)
    Optional: Local Ollama (llama3.1:8b, nomic-embed-text)
```

---

## Prerequisites

| Dependency | Notes |
|---|---|
| Python 3.10+ | 3.11 recommended |
| **OpenRouter / OpenAI API Key** | **Primary inference provider** (fast, cloud-hosted) |
| [Ollama](https://ollama.com) (Optional) | Optional local offline LLM alternative |

### 1. Primary Setup: OpenRouter / OpenAI API (Recommended)
Set your API key and base URL in `.env`:
```bash
OPENAI_API_KEY="sk-or-v1-..."
OPENAI_BASE_URL="https://openrouter.ai/api/v1"
OPENAI_MODEL="openai/gpt-4o-mini"
OPENAI_EMBED_MODEL="text-embedding-3-small"
LLM_PROVIDER="openai"
```

### 2. Optional Setup: Local Ollama (Offline / $0)
If you prefer running fully local without API keys:
```bash
# Pull the required models
ollama pull llama3.1:8b          # chat / reasoning (~4.7 GB)
ollama pull nomic-embed-text     # embeddings (~270 MB)

# Set in .env:
LLM_PROVIDER="ollama"
OLLAMA_CHAT_MODEL="llama3.1:8b"
OLLAMA_EMBED_MODEL="nomic-embed-text"
```

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/mcp-deep-research-agent.git
cd mcp-deep-research-agent

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install runtime dependencies
pip install -r requirements.txt

# 4. Install Playwright browser (for JS-heavy pages)
playwright install chromium

# 5. Configure environment
cp .env.example .env
# Edit .env if you want to change models or paths

# 6. Initialise the database
python scripts/init_db.py
```

---

## Usage

### CLI

```bash
# Run a research query (Ollama must be running: ollama serve)
research ask "What are the trade-offs between REST and GraphQL?" --format report

# Comparison table
research ask "Compare Redis, Memcached, and Valkey" --format comparison

# Use MLA citations
research ask "History of the internet" --format brief --style mla

# Try it without Ollama (demo/offline mode)
research ask "Compare React and Vue" --format comparison --demo

# List past sessions
research sessions list

# Recall a specific memory across all sessions
research sessions recall all --query "event sourcing"

# Export last session to Markdown
research export --output my-findings.md

# Health check
research doctor

# Launch the Streamlit UI
research ui

# Run the MCP server (for external MCP clients like Claude Desktop)
research serve
```

### Streamlit Web UI

```bash
streamlit run src/ui/app.py
# or simply:
research ui
```

The UI features:
- **Live research log** tracing every tool call as the agent works
- **Demo mode toggle** -- explore the UI offline without Ollama
- **Session history sidebar** with semantic memory search
- **One-click Markdown download** of the final report

---

## Configuration

All settings live in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | Inference backend: `openai` (primary / OpenRouter) or `ollama` (optional local) |
| `OPENAI_API_KEY` | `""` | OpenRouter, OpenAI, Groq, or DeepSeek API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model identifier (e.g. `openai/gpt-4o-mini`) |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Endpoint base (use `https://openrouter.ai/api/v1` for OpenRouter) |
| `OPENAI_EMBED_MODEL` | `text-embedding-3-small` | Cloud embedding model |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL (optional local fallback) |
| `OLLAMA_CHAT_MODEL` | `llama3.1:8b` | Local chat/reasoning model |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Local embedding model |
| `LLM_TEMPERATURE` | `0.2` | Lower = more factual |
| `ENABLE_CACHE` | `true` | Multi-tier SQLite & in-memory caching |
| `RESEARCH_DB_PATH` | `data/research.db` | SQLite database |
| `CHROMA_DIR` | `data/chroma` | ChromaDB vector store |
| `MAX_RESULTS_PER_QUERY` | `5` | Results per sub-question |
| `SOURCES_TO_SCRAPE` | `3` | Pages to read per sub-question |
| `MEMORY_RELEVANCE_THRESHOLD` | `0.75` | Cosine similarity cutoff for recall |
| `SEARCH_TIMEOUT` | `8` | Search network timeout (seconds) |
| `SCRAPE_TIMEOUT` | `8` | Scraping timeout (seconds) |
| `RESPECT_ROBOTS_TXT` | `true` | Honour robots.txt |

---

## Project Structure

```
mcp-deep-research-agent/
+-- README.md
+-- pyproject.toml           # build + tool config (ruff, mypy, pytest)
+-- requirements.txt         # runtime dependencies
+-- requirements-dev.txt     # dev/test dependencies
+-- .env.example             # config template
+-- .github/workflows/ci.yml # GitHub Actions CI
+-- scripts/
|   +-- init_db.py           # one-time DB + Chroma setup
+-- src/
|   +-- config.py            # Settings dataclass (env -> typed config)
|   +-- logging_utils.py     # rotating file logger + log_call context manager
|   +-- mcp_server.py        # FastMCP server (all 6 MCP tools)
|   +-- tools/
|   |   +-- search.py        # web_search via DuckDuckGo
|   |   +-- scrape.py        # scrape_page (static + Playwright fallback)
|   |   +-- citation.py      # generate_citation (APA-7 + MLA-9)
|   |   +-- memory.py        # store_memory / recall_memory
|   |   +-- formatter.py     # format_output (Brief / Comparison / Report)
|   |   +-- models.py        # SearchResult pydantic model
|   +-- agent/
|   |   +-- graph.py         # LangGraph state machine + ResearchAgent
|   |   +-- state.py         # ResearchState TypedDict + AgentDeps
|   |   +-- llm.py           # OllamaLLM + loads_lenient JSON parser
|   |   +-- tool_client.py   # in-process ToolClient (mirrors MCP surface)
|   |   +-- demo.py          # DemoLLM -- deterministic offline stand-in
|   |   +-- nodes/
|   |       +-- planner.py   # Planner node: query -> sub-questions
|   |       +-- researcher.py# Researcher: recall -> search -> scrape
|   |       +-- synthesizer.py # Synthesizer: LLM claim + citations + memory
|   |       +-- formatter.py # Formatter: render + persist session
|   +-- memory/
|   |   +-- sqlite_store.py  # sessions, findings, citations, memory pointers
|   |   +-- vector_store.py  # ChromaDB wrapper (cosine similarity)
|   |   +-- embeddings.py    # OllamaEmbeddings + HashingEmbeddings (offline)
|   +-- cli/
|   |   +-- main.py          # Typer CLI (ask, sessions, export, doctor, ui)
|   +-- ui/
|       +-- app.py           # Streamlit "The Night Desk" web interface
|       +-- assets/styles.css# CSS design system (dark ink + brass accent)
+-- tests/
|   +-- conftest.py          # shared fixtures (offline_agent, fake_vector, ...)
|   +-- fakes.py             # FakeVectorStore + FakeLLM
|   +-- unit/                # 63 unit tests (no network, no Ollama)
|   +-- integration/         # agent graph + MCP round-trip tests
+-- data/                    # created at runtime (gitignored)
    +-- research.db          # SQLite
    +-- chroma/              # ChromaDB
```

---

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run the full test suite (unit + integration, no Ollama required)
pytest -m "not e2e" -v

# Lint
ruff check src tests

# Format check
ruff format --check src tests

# Type check
mypy src/tools src/memory

# Coverage report
pytest --cov=src --cov-report=term-missing -m "not e2e"
```

### Running E2E tests (requires Ollama + network)

```bash
ollama serve   # in a separate terminal
pytest -m e2e -v
```

---

## Cost

**$0.00 -- verified.**

Every dependency is free/open-source. The only "cost" is electricity for local inference.

| Component | Service | Cost |
|---|---|---|
| LLM inference | Ollama (local) | $0 |
| Embeddings | Ollama nomic-embed-text (local) | $0 |
| Web search | DuckDuckGo (no API key) | $0 |
| Scraping | httpx + BeautifulSoup + Playwright | $0 |
| Memory | SQLite + ChromaDB embedded | $0 |
| CI/CD | GitHub Actions (public repo) | $0 |

---

## Security

- No credentials stored in plaintext
- `robots.txt` respected before scraping
- Scraped HTML is stripped of scripts/styles before reaching the LLM (prompt-injection defence)
- No telemetry -- nothing leaves your machine except the searches the agent runs

---

## License

MIT
