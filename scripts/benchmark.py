"""Benchmark script comparing Deep Research Agent latency, per-node overhead, and profiling metrics."""
from __future__ import annotations

import time
import json
from src.agent.graph import ResearchAgent
from src.config import get_settings


def run_benchmark(query: str, format_type: str = "report") -> dict:
    settings = get_settings()
    agent = ResearchAgent.from_settings(settings)

    t0 = time.perf_counter()
    state = agent.run(query, output_format=format_type)
    total_time = round(time.perf_counter() - t0, 2)

    findings = state.get("findings", [])
    total_citations = sum(len(f.get("citations", [])) for f in findings)
    papers = []
    for f in findings:
        for p in f.get("papers", []):
            if p.get("title") not in [x.get("title") for x in papers]:
                papers.append(p)

    metrics = state.get("metrics", {})

    return {
        "query": query,
        "total_time_seconds": total_time,
        "node_latencies": metrics.get("node_latencies", {}),
        "operation_counts": metrics.get("operation_counts", {}),
        "operation_durations": metrics.get("operation_durations", {}),
        "tokens": metrics.get("tokens", {}),
        "findings_count": len(findings),
        "unique_papers_count": len(papers),
        "citations_count": total_citations,
        "warnings_count": len(state.get("warnings", [])),
    }


if __name__ == "__main__":
    queries = [
        "Context Rot in Large Language Models",
        "Retrieval-Augmented Generation (RAG)",
        "Transformer Attention Mechanism",
    ]
    results = []
    for q in queries:
        print(f"\n==================================================")
        print(f"BENCHMARKING: {q}")
        print(f"==================================================")
        res = run_benchmark(q)
        print(json.dumps(res, indent=2))
        results.append(res)
