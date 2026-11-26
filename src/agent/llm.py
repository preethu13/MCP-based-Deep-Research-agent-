"""Local LLM wrapper around Ollama chat (F-02 reasoning engine).

Exposes a tiny :class:`LLM` protocol so the whole agent can be driven by a fake
model in tests — no Ollama, no network.  :class:`OllamaLLM` is the production
implementation; it also offers lenient JSON parsing for the planner and a
``ping`` health check for fail-fast startup (reliability 4.6).
"""

from __future__ import annotations

import json
import re
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLM(Protocol):
    def complete(self, system: str, user: str, temperature: float | None = None) -> str:
        ...


def _extract(resp: Any, *keys: str) -> Any:
    """Walk nested dict/attribute access on an Ollama response object."""
    current = resp
    for key in keys:
        try:
            current = current[key]
        except (TypeError, KeyError):
            current = getattr(current, key)
    return current


def loads_lenient(text: str) -> Any:
    """Best-effort JSON extraction from a chatty LLM response.

    Tries a direct parse, then the first ``[...]`` / ``{...}`` block found.
    Raises ``ValueError`` if nothing parses.
    """
    text = text.strip()
    # Strip Markdown code fences if present.
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    raise ValueError("no JSON found in response")


class OllamaLLM:
    """Chat completions via a local Ollama server."""

    def __init__(
        self,
        model: str = "llama3.1:8b",
        host: str = "http://localhost:11434",
        temperature: float = 0.2,
    ):
        self.model = model
        self.host = host
        self.temperature = temperature
        self._client_obj: Any = None

    def _client(self) -> Any:
        if self._client_obj is None:
            import ollama  # lazy import

            self._client_obj = ollama.Client(host=self.host)
        return self._client_obj

    def complete(self, system: str, user: str, temperature: float | None = None, max_tokens: int = 350) -> str:
        options: dict[str, Any] = {
            "temperature": self.temperature if temperature is None else temperature,
        }
        if max_tokens > 0:
            options["num_predict"] = max_tokens

        from src.agent.profiler import get_profiler
        prof = get_profiler()

        with prof.measure_operation("llm_inference"):
            resp = self._client().chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                options=options,
            )
            prompt_tokens = int(_extract(resp, "prompt_eval_count") or 0)
            eval_tokens = int(_extract(resp, "eval_count") or 0)
            prof.record_tokens(prompt_tokens=prompt_tokens, completion_tokens=eval_tokens)
            return str(_extract(resp, "message", "content")).strip()

    def complete_json(self, system: str, user: str, temperature: float | None = None, max_tokens: int = 350) -> Any:
        raw = self.complete(system, user, temperature, max_tokens=max_tokens)
        return loads_lenient(raw)

    def ping(self) -> tuple[bool, str]:
        """Return ``(ok, message)`` describing Ollama availability."""
        try:
            self._client().list()
            return True, "ok"
        except Exception as exc:
            return False, str(exc)
