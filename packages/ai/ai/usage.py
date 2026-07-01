"""LLM token/cost accounting (BLUEPRINT.md §3 Week 5).

Accumulates tokens across real LLM calls (the template path costs nothing). Prices
are per-1M-token list rates; override via env if they change. Read the totals for a
metrics endpoint or cost dashboard.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Opus 4.8 list price (USD per 1M tokens); override if you switch models.
_INPUT_PER_MTOK = float(os.getenv("CLOUDTRIM_LLM_INPUT_PER_MTOK", "5.0"))
_OUTPUT_PER_MTOK = float(os.getenv("CLOUDTRIM_LLM_OUTPUT_PER_MTOK", "25.0"))


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def estimated_cost_usd(self) -> float:
        return round(
            self.input_tokens / 1_000_000 * _INPUT_PER_MTOK
            + self.output_tokens / 1_000_000 * _OUTPUT_PER_MTOK,
            6,
        )

    def record(self, input_tokens: int, output_tokens: int) -> None:
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def reset(self) -> None:
        self.calls = self.input_tokens = self.output_tokens = 0


usage = Usage()


def record_response(resp: object) -> None:
    """Pull usage off a LLM response if present (no-op for the template path)."""
    u = getattr(resp, "usage", None)
    if u is None:
        return
    usage.record(int(getattr(u, "input_tokens", 0) or 0), int(getattr(u, "output_tokens", 0) or 0))
