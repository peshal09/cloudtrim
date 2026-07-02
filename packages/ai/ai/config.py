"""AI layer configuration (BLUEPRINT.md §6).

The LLM is used only when a provider is configured (base URL + model + key);
otherwise the deterministic template path runs. Determinism-first: tests/eval/demo
work with no LLM. See the memory note on the deterministic offline path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AIConfig:
    api_key: str | None = None
    base_url: str = ""  # OpenAI-compatible endpoint; no provider baked in
    model: str = ""
    max_tokens: int = 1024
    max_retries: int = 2
    max_prompt_chars: int = 20_000  # guardrail: skip the LLM on oversized prompts

    @property
    def enabled(self) -> bool:
        """True when a real LLM call is possible; False -> template path."""
        return bool(self.api_key and self.base_url and self.model)

    @classmethod
    def from_env(cls) -> AIConfig:
        return cls(
            api_key=os.getenv("CLOUDTRIM_LLM_API_KEY") or None,
            base_url=os.getenv("CLOUDTRIM_LLM_BASE_URL", ""),
            model=os.getenv("CLOUDTRIM_LLM_MODEL", ""),
        )
