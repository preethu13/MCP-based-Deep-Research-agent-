# System Evaluation, Benchmark & Test Suite Documentation

Welcome to the **Evaluation & Benchmarks** documentation directory for the **MCP-Powered Deep Research Agent**.

This directory provides comprehensive documentation covering empirical performance benchmarks, test suite execution logs, retrieval-augmented grounding metrics, and operational reliability standards.
This directory provides empirical benchmarks, architecture evaluations, test suite execution audits, and factual grounding metrics for the agent's live search, scraping, and synthesis pipeline.

---

## 📑 Directory Contents

| Document | Description | Key Focus Areas |
| :--- | :--- | :--- |
| [**1. SYSTEM_EVALUATION.md**](./SYSTEM_EVALUATION.md) | Architectural evaluation & subsystem analysis | DAG pipeline, in-process vs FastMCP, vector store, SQLite persistence |
| [**1. SYSTEM_EVALUATION.md**](./SYSTEM_EVALUATION.md) | Architectural evaluation & subsystem analysis | DAG pipeline, in-process vs FastMCP, SQLite store, error containment |
| [**2. BENCHMARK_METRICS.md**](./BENCHMARK_METRICS.md) | Quantitative performance benchmarks | Latency breakdown, token efficiency, scraping throughput, concurrency |
| [**3. RAG_AND_GROUNDING_EVALUATION.md**](./RAG_AND_GROUNDING_EVALUATION.md) | Retrieval quality & factual grounding rubrics | Precision@K, citation accuracy, false-friend filtering, hallucination rate |
| [**4. TEST_RESULTS.md**](./TEST_RESULTS.md) | Real-world pytest suite audit & coverage report | Unit, integration, E2E test runs, failure containment verification |
| [**3. SEARCH_AND_GROUNDING_EVALUATION.md**](./SEARCH_AND_GROUNDING_EVALUATION.md) | Search quality, scraping & factual grounding | Precision@K, citation provenance, false-friend filtering, hallucination rate |
| [**4. TEST_RESULTS.md**](./TEST_RESULTS.md) | Test suite audit & safety verification | Unit, integration, E2E test runs, failure containment verification |

---

## 🎯 Evaluation Objectives

1. **Zero-Exception Resilience:** Confirm all tools degrade gracefully when web scraping, academic APIs, or LLMs encounter network or rate-limit faults.
2. **Deterministic Grounding:** Evaluate citation provenance and ensure that every synthesized assertion maps to a real scraped snippet or peer-reviewed DOI.
3. **Execution Latency:** Measure end-to-end execution across 4 graph stages (`planner` $\rightarrow$ `researcher` $\rightarrow$ `synthesizer` $\rightarrow$ `formatter`) for `brief`, `detailed`, and `comparative` modes.
4. **FastMCP & In-Process Parity:** Ensure equal tool invocation reliability between the native CLI/Web UI and external MCP desktop clients.
