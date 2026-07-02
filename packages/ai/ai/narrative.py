"""Analysis-wide prioritization narrative (BLUEPRINT.md §3 Week 2, §6).

"Fix these first, and here's why" across the whole analysis — the same bounded-LLM
law as explain_finding: the LLM when configured, a deterministic architect-voice
template otherwise, with dollar figures validated against the engine's aggregate on
both paths.
"""

from __future__ import annotations

from collections.abc import Callable

from engine.aggregate import AnalysisAggregate
from engine.models import ExplanationSource
from pydantic import BaseModel

from ai.config import AIConfig
from ai.llm import run_llm
from ai.validation import validate_amounts

_SYSTEM = (
    "You are a senior cloud architect giving an engineer a prioritized plan to cut "
    "cloud cost. Be concise (3-5 sentences): the total opportunity, which 2-3 items "
    "to do first and why (savings and rollout risk), and any low-risk quick wins. "
    "CRITICAL: state ONLY the dollar figures provided, verbatim — never invent or "
    "recompute an amount."
)


class Narrative(BaseModel):
    text: str
    source: ExplanationSource


def _money(v: float) -> str:
    return f"${v:,.2f}"


def _allowed(agg: AnalysisAggregate) -> set[float]:
    allowed = {agg.realistic_monthly_savings, agg.gross_monthly_savings, 0.0}
    allowed.update(o.monthly_savings for o in agg.top_opportunities)
    return allowed


def render_template(agg: AnalysisAggregate) -> str:
    ops = [o for o in agg.top_opportunities if o.monthly_savings > 0]
    if not ops:
        return (
            "No dollar-saving changes were found. The remaining findings are "
            "governance/hygiene items with no direct cost impact."
        )
    top = ops[:3]
    lead = (
        f"CloudTrim identified {_money(agg.realistic_monthly_savings)}/mo in realizable "
        f"savings. Prioritized by impact and risk:"
    )
    lines = [
        f"{i}. {o.resource_identifier} — {o.title.lower()}: save "
        f"{_money(o.monthly_savings)}/mo (risk: {o.risk})."
        for i, o in enumerate(top, 1)
    ]
    pct = round(top[0].monthly_savings / agg.realistic_monthly_savings * 100)
    closer = (
        f"Start with {top[0].resource_identifier} — it alone is ~{pct}% of the total, "
        f"at {top[0].risk} rollout risk."
    )
    return "\n".join([lead, *lines, closer])


def prioritize_analysis(
    agg: AnalysisAggregate,
    config: AIConfig | None = None,
    client_factory: Callable[[AIConfig], object] | None = None,
) -> Narrative:
    config = config or AIConfig.from_env()
    allowed = _allowed(agg)

    if config.enabled:
        text = _try_llm(agg, config, client_factory)
        if text and validate_amounts(text, allowed)[0]:
            return Narrative(text=text, source=ExplanationSource.LLM)

    template = render_template(agg)
    if not validate_amounts(template, allowed)[0]:  # defensive; template is grounded
        template = (
            f"{_money(agg.realistic_monthly_savings)}/mo in realizable savings across "
            f"{len(agg.top_opportunities)} opportunities."
        )
    return Narrative(text=template, source=ExplanationSource.TEMPLATE)


def _build_prompt(agg: AnalysisAggregate) -> str:
    lines = [
        f"Total realizable savings: {_money(agg.realistic_monthly_savings)}/mo "
        f"(gross {_money(agg.gross_monthly_savings)}/mo).",
        "Top opportunities (use ONLY these dollar figures, verbatim):",
    ]
    for o in agg.top_opportunities:
        lines.append(
            f"  - {o.resource_identifier}: {o.title} — {_money(o.monthly_savings)}/mo, "
            f"severity {o.severity.value}, risk {o.risk}"
        )
    lines.append("\nWrite the prioritized plan.")
    return "\n".join(lines)


def _try_llm(
    agg: AnalysisAggregate,
    config: AIConfig,
    client_factory: Callable[[AIConfig], object] | None,
) -> str | None:
    return run_llm(_SYSTEM, _build_prompt(agg), config, client_factory)
