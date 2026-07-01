"""AI layer configuration (BLUEPRINT.md §6).

LLM is used only when a key is present; otherwise the deterministic template
path runs. Determinism-first: tests/eval/demo work with no key. See the memory
note on the deterministic offline path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AIConfig:
    api_key: str | None = None
    model: str = "LLM-opus-4-8"
    max_tokens: int = 1024
    max_retries: int = 2

    @property
    def enabled(self) -> bool:
        """True when a real LLM call is possible; False -> template path."""
        return bool(self.api_key)

    @classmethod
    def from_env(cls) -> AIConfig:
        return cls(
            api_key=os.getenv("CLOUDTRIM_LLM_API_KEY") or None,
            model=os.getenv("CLOUDTRIM_LLM_MODEL", "LLM-opus-4-8"),
        )
