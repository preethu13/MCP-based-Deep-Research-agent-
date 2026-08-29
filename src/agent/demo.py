"""Offline demo LLM (no Ollama required).

A deterministic, network-free stand-in for :class:`OllamaLLM` that produces
plausible — clearly labelled — output so the UI and CLI can be explored before
Ollama is installed.  It never fabricates sources: synthesis only echoes and
condenses whatever real scraped/recalled context it is given.

Enable with ``research ask --demo`` or the "Demo mode" toggle in the web UI.
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.agent.llm import loads_lenient
from src.agent.nodes.planner import _heuristic_decompose


def _extract_after(text: str, marker: str) -> str:
    idx = text.find(marker)
    return text[idx + len(marker) :].strip() if idx != -1 else ""


def _first_sentences(text: str, n: int = 2) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    joined = " ".join(s for s in sentences[:n] if s).strip()
    return joined


class DemoLLM:
    """Deterministic offline stand-in for the chat model."""

    def complete(self, system: str, user: str, temperature: float | None = None) -> str:
        s = system.lower()

        # Planner: return a JSON array of sub-questions.
        if "research planner" in s:
            query = _extract_after(user, "User question:").split("\n")[0].strip()
            subs = _heuristic_decompose(query)
            if len(subs) == 1:
                subs = [
                    f"What is {query}?",
                    f"What are the key facts and context around {query}?",
                    f"What are the trade-offs or debates about {query}?",
                ]
            return json.dumps(subs)

        # Comparison structuring: return entities x dimensions JSON.
        if "structured comparison" in s or "convert research notes" in s:
            query = _extract_after(user, "Question:").split("\n")[0].strip()
            parts = re.split(r"\s+vs\.?\s+|\s+versus\s+|,\s*", query, flags=re.IGNORECASE)
            names = [p.strip() for p in parts if p.strip()][:4] or ["Option A", "Option B"]
            entities = [
                {
                    "name": name,
                    "attributes": {
                        "Overview": f"Demo summary for {name}",
                        "Best for": "General use",
                        "Trade-off": "See full report",
                    },
                }
                for name in names
            ]
            return json.dumps({"dimensions": ["Overview", "Best for", "Trade-off"], "entities": entities})

        # Synthesis: condense the provided context — never invent.
        if "research analyst" in s:
            context = _extract_after(user, "Sources:")
            sub_q = _extract_after(user, "Sub-question:").split("\n")[0].strip()
            summary = _first_sentences(context, 2)
            if summary:
                return f"{summary} (Demo mode: condensed locally without an LLM.)"
            return f"No source text was available for “{sub_q}” in demo mode."

        return ""

    def complete_json(self, system: str, user: str, temperature: float | None = None) -> Any:
        return loads_lenient(self.complete(system, user, temperature))

    def ping(self) -> tuple[bool, str]:
        return True, "demo mode (no Ollama)"
