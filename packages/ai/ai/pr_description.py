"""PR description generator (BLUEPRINT.md §3 Week 4, §6).

Writes the title + body for a fix PR, grounded on the deterministic patches and
savings. Same bounded-LLM law: LLM when a key is set, a template otherwise, with
dollar figures validated against the engine's numbers on both paths.
"""

from __future__ import annotations

from collections.abc import Callable

from engine.models import ExplanationSource, Finding
from pydantic import BaseModel

from ai.config import AIConfig
from ai.validation import validate_amounts

_SYSTEM = (
    "You are a senior cloud engineer writing the body of a pull request that applies "
    "cost fixes. Be concise and factual: what changed, per-resource, and the total "
    "monthly savings. CRITICAL: state ONLY the dollar figures provided, verbatim — "
    "never invent or recompute an amount."
)


class PRDescription(BaseModel):
    title: str
    body: str
    source: ExplanationSource


def _money(v: float) -> str:
    return f"${v:,.2f}"


def _total(findings: list[Finding]) -> float:
    return round(sum(f.monthly_savings for f in findings), 2)


def render_template(findings: list[Finding]) -> str:
    total = _total(findings)
    n = len(findings)
    plural = "s" if n != 1 else ""
    lines = [
        f"## CloudTrim — {n} cost fix{'es' if n != 1 else ''}",
        "",
        f"This PR rightsizes {n} resource{plural} flagged by CloudTrim, saving an "
        f"estimated {_money(total)}/mo. Each change is a minimal, validated edit.",
        "",
        "| Resource | Change | Savings/mo | Risk |",
        "|---|---|---|---|",
    ]
    for f in findings:
        ident = f.id.split(":", 1)[1]
        cur = f.evidence.get("current_instance_type", "?")
        tgt = f.evidence.get("target_instance_type", "?")
        lines.append(
            f"| `{ident}` | {cur} → {tgt} | {_money(f.monthly_savings)} | {f.risk.value} |"
        )
    lines += ["", "_Numbers are computed by the CloudTrim engine, not an LLM._"]
    return "\n".join(lines)


def describe_pr(
    findings: list[Finding],
    config: AIConfig | None = None,
    client_factory: Callable[[AIConfig], object] | None = None,
) -> PRDescription:
    config = config or AIConfig.from_env()
    total = _total(findings)
    n = len(findings)
    title = f"CloudTrim: rightsize {n} resource{'s' if n != 1 else ''} (save {_money(total)}/mo)"
    allowed = {total, 0.0} | {f.monthly_savings for f in findings}

    if config.enabled:
        body = _try_llm(findings, config, client_factory)
        if body and validate_amounts(body, allowed)[0]:
            return PRDescription(title=title, body=body, source=ExplanationSource.LLM)

    body = render_template(findings)
    if not validate_amounts(body, allowed)[0]:  # defensive; template is grounded
        body = f"Rightsizes {n} resources, saving {_money(total)}/mo."
    return PRDescription(title=title, body=body, source=ExplanationSource.TEMPLATE)


def _build_prompt(findings: list[Finding]) -> str:
    lines = [
        f"Total monthly savings: {_money(_total(findings))} (use verbatim).",
        "Changes (use ONLY these dollar figures):",
    ]
    for f in findings:
        ident = f.id.split(":", 1)[1]
        cur = f.evidence.get("current_instance_type", "?")
        tgt = f.evidence.get("target_instance_type", "?")
        lines.append(
            f"  - {ident}: {cur} -> {tgt}, {_money(f.monthly_savings)}/mo, risk {f.risk.value}"
        )
    lines.append("\nWrite the PR body (markdown).")
    return "\n".join(lines)


def _try_llm(
    findings: list[Finding],
    config: AIConfig,
    client_factory: Callable[[AIConfig], object] | None,
) -> str | None:
    try:
        if client_factory:
            client = client_factory(config)
        else:
            import LLM

            client = LLM.LLM(api_key=config.api_key, max_retries=config.max_retries)
        resp = client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _build_prompt(findings)}],
        )
        if getattr(resp, "stop_reason", None) == "refusal":
            return None
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return text.strip() or None
    except Exception:  # noqa: BLE001 — never fail on an explainer error
        return None
