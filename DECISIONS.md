# DECISIONS.md — Architecture Decision Records (ADRs)

> **Repository:** MCP-Powered Deep Research Agent  
> **Status:** Accepted / Active  

---

## ADR 01: LangGraph for Workflow Orchestration

- **Decision:** Use **LangGraph** (v0.2+) to define an explicit cyclic state machine (`ResearchState`) instead of linear scripts, AutoGen, or CrewAI.
- **Context:** Research pipelines require stateful progression: question planning, multi-source searching, context aggregation, batch synthesis, and formatting.
- **Why Chosen:**
  - Full control over deterministic execution order (`START -> planner -> researcher -> synthesizer -> formatter -> END`).
  - Native streaming API (`graph.stream()`) makes live UI trace telemetry trivial to implement.
  - Testable with standard dependency injection (`AgentDeps`).
- **Alternatives Considered:**
  - *AutoGen / CrewAI:* Too conversational and non-deterministic; high risk of agent loops and runaway token usage.
  - *Plain Python Scripts:* Lacked unified state threading, event logging, and future multi-hop branching capability.
- **Limitations:** Learning curve for LangGraph state immutability; graph compilation overhead.

---

## ADR 02: Dual Memory Architecture (SQLite + ChromaDB)

- **Decision:** Split persistence between **SQLite** for relational session/citation records and **ChromaDB** for semantic embeddings.
- **Context:** The system needs both relational integrity (foreign keys linking sessions to findings and findings to citations) and fuzzy semantic recall across past queries.
- **Why Chosen:**
  - SQLite provides ACID transactions, zero-config file storage (`data/research.db`), and cascading deletes.
  - ChromaDB provides lightweight, embedded vector search without requiring standalone database services (like PostgreSQL with pgvector or Pinecone).
  - Explicit pointer table (`memories.chroma_vector_id`) links relational findings to vector documents.
- **Alternatives Considered:**
  - *ChromaDB Only:* Insufficient for relational queries (finding all citations for a session, filtering by author/publisher).
  - *PostgreSQL + pgvector:* Too heavy for a single-user $0-cost local setup.
- **Limitations:** ChromaDB file storage format changes across major versions; manual synchronization required between SQLite and Chroma.

---

## ADR 03: In-Process Tool Execution with FastMCP Protocol Parity

- **Decision:** The agent executes tools in-process via `src/agent/tool_client.py` rather than calling the FastMCP server via network/IPC.
- **Context:** FastMCP is designed for RPC (over stdio or SSE). Calling tools over IPC inside a local Python loop introduces serialization latency and process management overhead.
- **Why Chosen:**
  - In-process execution is instantaneous (zero IPC latency).
  - Maintains full compatibility with external MCP clients (Claude Desktop) through `src/mcp_server.py`.
- **Alternatives Considered:**
  - *Pure FastMCP Subprocess Client:* High latency for multi-query execution.
- **Limitations:** Dual maintenance: tools added to `src/tools/` must be wired into both `ToolClient` and `mcp_server.py`.

---

## ADR 04: OpenAlex API Integration for Scientific Literature

- **Decision:** Use the **OpenAlex REST API** as the primary scientific literature index, supplementing DuckDuckGo.
- **Context:** General web search engines (DuckDuckGo) often index blog posts, SEO articles, and forum posts rather than primary research papers, causing shallow or unreliable citations.
- **Why Chosen:**
  - Catalogs 250M+ scientific publications with zero cost and no API keys.
  - Returns verified DOIs, author rosters, publication years, and reconstructed abstracts directly in the API payload.
  - Open-access PDF links allow instant paper access.
- **Alternatives Considered:**
  - *Semantic Scholar API:* Requires rate-limited API keys.
  - *arXiv API:* Only covers physics/math/CS preprints; lacks peer-reviewed journal indexing.
- **Limitations:** Reconstructing abstracts from inverted indices (`abstract_inverted_index`) adds minor CPU string manipulation; rate limits apply for aggressive polling.

---

## ADR 05: Query Sanitization & Heuristic Relevance Scoring over Raw BM25

- **Decision:** Pre-process search queries with `clean_search_query()` and filter results with `score_paper_relevance()`.
- **Context:** When users input specific queries (e.g., *"context rot in llm"*), the Planner generates long sentences like *"What are the potential consequences and mitigation strategies for context rot in real-world LLM applications?"*. Sending this raw sentence caused OpenAlex BM25 to match financial bias mitigation papers and adversarial trojans (`Concept-ROT`).
- **Why Chosen:**
  - Stripping conversational stopwords eliminates keyword dilution.
  - Heuristic scoring penalizes off-topic acronym collisions and unrelated domain vocabulary (e.g. stock investing).
  - Negative scores are discarded, preventing garbage-in/garbage-out synthesis.
- **Alternatives Considered:**
  - *Local Neural Cross-Encoder Reranker (e.g. BGE-Reranker):* Better semantic accuracy, but requires downloading 300MB+ model weights and adds GPU/CPU inference latency.
- **Limitations:** Heuristics must be maintained as new domains and acronyms emerge.

---

## ADR 06: Abstract Fast-Path & Batch LLM Synthesis for Latency Reduction

- **Decision:** Bypass web scraping when OpenAlex provides full abstracts, and combine multiple sub-question findings into a single batch LLM call.
- **Context:** The initial prototype took >200 seconds per research run due to sequential HTML page scraping and sequential LLM calls.
- **Why Chosen:**
  - Papers with abstracts can be processed in milliseconds without network scraping.
  - Batch synthesis reduces LLM round-trips from 3 sequential calls to 1 coordinated call, reducing execution time to ~15-25 seconds.
- **Alternatives Considered:**
  - *Parallel LLM Inference:* Local Ollama instances typically queue concurrent requests sequentially on consumer GPUs, so concurrent calls do not reduce wall-clock time.
- **Limitations:** Batch synthesis prompt must fit within model context windows (token limits clamped).

---

## ADR 07: Primary OpenRouter Cloud API Inference with Optional Local Ollama

- **Decision:** Use **OpenRouter / Cloud API** (`src/agent/api_llm.py`) with `gpt-4o-mini` and `text-embedding-3-small` as the primary inference & embeddings engine, with local **Ollama** (`llama3.1:8b`, `nomic-embed-text`) as an optional offline alternative.
- **Context:** Local 8B models can be slow on consumer hardware without dedicated GPUs. OpenRouter provides ultra-fast inference and high-accuracy synthesis without local hardware constraints.
- **Why Chosen:**
  - Fast, responsive completions via lightweight `httpx` client without heavy SDK dependencies.
  - Consistent embeddings using `text-embedding-3-small` via OpenAI / OpenRouter endpoints.
  - Configurable via `.env` (`OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`, `OPENAI_EMBED_MODEL`).
  - Full local privacy preserved whenever users toggle `LLM_PROVIDER=ollama`.
- **Alternatives Considered:**
  - *Ollama-only:* Required 8-16GB RAM and had high per-token latency on CPU-only machines.
  - *Official OpenAI Python SDK:* Heavy dependency footprint with frequent breaking changes.
- **Limitations:** Cloud mode requires user-supplied API keys and internet access.

---

## ADR 08: Multi-Tier Caching & Instant Research Recall

- **Decision:** Implement multi-tier caching across search queries, embeddings, scraped pages, and completed research sessions in SQLite (`data/research.db`).
- **Context:** Repeated or related research queries (e.g. searching "Context Rot") previously re-executed the entire retrieval and LLM synthesis pipeline from scratch, taking 25-35 seconds each time.
- **Why Chosen:**
  - In-memory LRU + persistent SQLite cache serves identical or previously completed research queries instantaneously (~0.05 seconds).
  - Preserves exact verified claims, findings, and APA/MLA citations.
  - Hash-based embedding cache prevents re-computing vectors for known strings.
- **Alternatives Considered:**
  - *Redis:* Required running an external server service; SQLite + in-memory dictionary provides zero-dependency persistence.
