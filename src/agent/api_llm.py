"""API-Key LLM and Embeddings Provider (OpenAI, Groq, DeepSeek, OpenRouter, etc.).

This module enables using cloud and hosted LLMs via standard API keys without
requiring a local Ollama runtime.  Built using ``httpx`` (already in dependencies),
requiring zero new external libraries.

Compatible with:
  - OpenAI (gpt-4o-mini, gpt-4o, gpt-3.5-turbo)
  - Groq (llama-3.1-8b-instant, mixtral-8x7b-32768)
  - DeepSeek (deepseek-chat, deepseek-coder)
  - OpenRouter (any hosted model)
  - Together AI, LMStudio, vLLM, or any OpenAI-compatible /v1 endpoint.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.agent.llm import loads_lenient

logger = logging.getLogger(__name__)


class OpenAILLM:
    """Chat completions client for OpenAI and OpenAI-compatible REST APIs."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.2,
        timeout: float = 30.0,
    ):
        self.api_key = (api_key or "").strip()
        self.model = (model or "gpt-4o-mini").strip()
        self.base_url = (base_url or "https://api.openai.com/v1").strip().rstrip("/")
        self.temperature = temperature
        self.timeout = timeout

    def complete(
        self,
        system: str,
        user: str,
        temperature: float | None = None,
        max_tokens: int = 400,
    ) -> str:
        """Call the chat completions endpoint."""
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is not configured. Set OPENAI_API_KEY in your .env or environment."
            )

        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature if temperature is None else temperature,
        }
        if max_tokens > 0:
            payload["max_tokens"] = max_tokens

        url = f"{self.base_url}/chat/completions"
        from src.agent.profiler import get_profiler
        prof = get_profiler()

        try:
            with prof.measure_operation("llm_inference"):
                resp = httpx.post(url, headers=headers, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                usage = data.get("usage") or {}
                prof.record_tokens(
                    prompt_tokens=int(usage.get("prompt_tokens", 0)),
                    completion_tokens=int(usage.get("completion_tokens", 0)),
                )
                return str(data["choices"][0]["message"]["content"]).strip()
        except httpx.HTTPStatusError as exc:
            err_msg = f"API error ({exc.response.status_code}): {exc.response.text[:200]}"
            logger.error(err_msg)
            raise RuntimeError(err_msg) from exc
        except Exception as exc:
            logger.error(f"Failed to communicate with LLM API at {url}: {exc}")
            raise

    def complete_json(
        self,
        system: str,
        user: str,
        temperature: float | None = None,
        max_tokens: int = 400,
    ) -> Any:
        """Complete and parse JSON response leniently."""
        raw = self.complete(system, user, temperature, max_tokens=max_tokens)
        return loads_lenient(raw)

    def ping(self) -> tuple[bool, str]:
        """Test API key and connectivity."""
        if not self.api_key:
            return False, "Missing OPENAI_API_KEY. Add it to your .env file."

        import httpx

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = httpx.get(f"{self.base_url}/models", headers=headers, timeout=6.0)
            if resp.status_code == 200:
                return True, f"API connected ({self.model})"
            return False, f"API returned status {resp.status_code}: {resp.text[:120]}"
        except Exception as exc:
            return False, f"Connection failed to {self.base_url}: {exc}"


class OpenAIEmbeddings:
    """Vector embeddings client using OpenAI /v1/embeddings endpoint."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ):
        self.api_key = (api_key or "").strip()
        self.model = (model or "text-embedding-3-small").strip()
        self.base_url = (base_url or "https://api.openai.com/v1").strip().rstrip("/")
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings vectors for a batch of texts."""
        if not texts:
            return []
        if not self.api_key:
            # Fall back to deterministic hashing embeddings if key is missing
            from src.memory.embeddings import HashingEmbeddings

            return HashingEmbeddings().embed(texts)

        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": list(texts),
        }

        try:
            resp = httpx.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            items = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in items]
        except Exception as exc:
            logger.warning(f"Embedding API failed ({exc}), falling back to HashingEmbeddings")
            from src.memory.embeddings import HashingEmbeddings

            return HashingEmbeddings().embed(texts)
