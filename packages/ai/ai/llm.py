"""Generic, provider-agnostic LLM client (BLUEPRINT.md §6).

A single place that talks to a configurable, OpenAI-compatible chat-completions
endpoint (`CLOUDTRIM_LLM_BASE_URL` / `_MODEL` / `_API_KEY`). No provider is baked in;
point it at any compatible gateway. Callers pass a system + user prompt and get text
back (or None on any failure), with token usage accounted centrally.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ai.config import AIConfig
from ai.usage import usage


@dataclass
class LLMResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class HttpLLMClient:
    def __init__(self, config: AIConfig) -> None:
        self._config = config

    def complete(self, system: str, user: str) -> LLMResult | None:
        import httpx

        resp = httpx.post(
            f"{self._config.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self._config.api_key}"},
            json={
                "model": self._config.model,
                "max_tokens": self._config.max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        if choice.get("finish_reason") == "content_filter":
            return None
        u = data.get("usage", {})
        return LLMResult(
            text=choice["message"]["content"] or "",
            input_tokens=int(u.get("prompt_tokens", 0) or 0),
            output_tokens=int(u.get("completion_tokens", 0) or 0),
        )


def run_llm(
    system: str,
    prompt: str,
    config: AIConfig,
    client_factory: Callable[[AIConfig], object] | None = None,
) -> str | None:
    """Best-effort completion: returns stripped text, or None on guard/error/empty."""
    if len(prompt) > config.max_prompt_chars:  # guardrail: don't send an oversized prompt
        return None
    try:
        client = client_factory(config) if client_factory else HttpLLMClient(config)
        result = client.complete(system, prompt)
    except Exception:  # noqa: BLE001 — never fail the analysis on an LLM error
        return None
    if result is None:
        return None
    usage.record(result.input_tokens, result.output_tokens)  # token/cost accounting
    return result.text.strip() or None
