"""Output validation — the structural guardrail (BLUEPRINT.md §6, ADR-0001).

Runs on BOTH the LLM and template paths (one code path), proving the guardrail is
structural, not LLM-specific: any dollar figure in the explanation must match one
of the engine's numbers for the finding. A template can't hallucinate, but we
validate it anyway so the invariant is enforced uniformly.
"""

from __future__ import annotations

import re

from engine.models import Finding

_MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")
_TOLERANCE = 0.01


def cited_amounts(text: str) -> list[float]:
    """Every $-denominated figure in the text, as floats."""
    out: list[float] = []
    for match in _MONEY.finditer(text):
        try:
            out.append(float(match.group(1).replace(",", "")))
        except ValueError:
            continue
    return out


def validate_amounts(text: str, allowed: set[float]) -> tuple[bool, list[float]]:
    """Return (ok, offending). Any cited $ not matching an allowed engine number fails."""
    offending = [
        amount
        for amount in cited_amounts(text)
        if not any(abs(amount - a) <= _TOLERANCE for a in allowed)
    ]
    return (not offending, offending)


def validate_explanation(text: str, finding: Finding) -> tuple[bool, list[float]]:
    """A finding's explanation may cite only its own engine numbers."""
    return validate_amounts(
        text,
        {
            round(finding.current_cost, 2),
            round(finding.projected_cost, 2),
            round(finding.monthly_savings, 2),
        },
    )
