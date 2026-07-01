"""explain_finding() — the bounded LLM entrypoint (BLUEPRINT.md §6).

Design (your three requirements):
  1. Architect-voice-lite template, from the same evidence the LLM gets.
  2. Validation runs on BOTH paths — one code path, structural guardrail.
  3. Every explanation is tagged explanation_source (template|llm), visible + testable.

LLM is used only when a key is configured; on any error, empty output, refusal,
or validation failure, we fall back to the template. The full flow therefore works
with zero keys — CI asserts the template path.
"""

from __future__ import annotations

from collections.abc import Callable

from engine.models import ExplanationSource, Finding, Resource

from ai.cache import cache, finding_key
from ai.config import AIConfig
from ai.templates import render_template
from ai.usage import record_response
from ai.validation import validate_explanation

_SYSTEM = (
    "You are a senior cloud architect explaining a single cost finding to the "
    "engineer who owns the infrastructure. Be concise (2-4 sentences), concrete, "
    "and practical: what's wrong, the fix, the dollar impact, and the rollback risk. "
    "CRITICAL: state ONLY the dollar figures provided to you, verbatim. Never invent, "
    "recompute, or round a dollar amount. Percentages and instance types may be quoted "
    "from the evidence."
)


def explain_finding(
    finding: Finding,
    resource: Resource | None,
    config: AIConfig | None = None,
    client_factory: Callable[[AIConfig], object] | None = None,
) -> Finding:
    config = config or AIConfig.from_env()

    key = finding_key(finding, config.model)
    cached = cache.get(key)
    if cached is not None:
        finding.explanation, source = cached
        finding.explanation_source = ExplanationSource(source)
        return finding

    text: str | None = None
    source = ExplanationSource.TEMPLATE

    if config.enabled:
        llm_text = _try_llm(finding, resource, config, client_factory)
        if llm_text and validate_explanation(llm_text, finding)[0]:
            text, source = llm_text, ExplanationSource.LLM

    if text is None:
        text = render_template(finding, resource)
        source = ExplanationSource.TEMPLATE

    # Uniform structural guardrail — the template must pass too.
    if not validate_explanation(text, finding)[0]:
        text = f"{finding.title} on `{finding.resource_id}` (risk: {finding.risk.value})."
        source = ExplanationSource.TEMPLATE

    finding.explanation = text
    finding.explanation_source = source
    cache.set(key, (text, source.value))
    return finding


def make_explainer(
    config: AIConfig | None = None,
) -> Callable[[Finding, Resource | None], None]:
    """A pipeline-compatible explain hook (mutates the finding in place)."""
    cfg = config or AIConfig.from_env()

    def _explain(finding: Finding, resource: Resource | None) -> None:
        explain_finding(finding, resource, cfg)

    return _explain


def _build_prompt(finding: Finding, resource: Resource | None) -> str:
    ident = resource.identifier if resource else finding.resource_id
    rtype = resource.type.value if resource else "resource"
    lines = [
        f"Finding: {finding.title}",
        f"Resource: {ident} ({rtype}, region={getattr(resource, 'region', None)})",
        f"Severity: {finding.severity.value}   Rollout risk: {finding.risk.value}",
        "Dollar figures (USD/month) — use ONLY these, verbatim:",
        f"  current_cost   = ${finding.current_cost:,.2f}",
        f"  projected_cost = ${finding.projected_cost:,.2f}",
        f"  monthly_savings= ${finding.monthly_savings:,.2f}",
        f"Evidence: {finding.evidence}",
        "",
        "Write the explanation.",
    ]
    return "\n".join(lines)


def _try_llm(
    finding: Finding,
    resource: Resource | None,
    config: AIConfig,
    client_factory: Callable[[AIConfig], object] | None,
) -> str | None:
    """Best-effort LLM call. Returns None on any failure (pipeline never fails)."""
    prompt = _build_prompt(finding, resource)
    if len(prompt) > config.max_prompt_chars:  # guardrail: don't send an oversized prompt
        return None
    try:
        client = client_factory(config) if client_factory else _default_client(config)
        resp = client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        record_response(resp)  # token/cost accounting
        if getattr(resp, "stop_reason", None) == "refusal":
            return None
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return text.strip() or None
    except Exception:  # noqa: BLE001 — never fail the analysis on an explainer error
        return None


def _default_client(config: AIConfig) -> object:
    import LLM  # lazy: optional dependency, only when a key is set

    # SDK retries 429/5xx/connection errors with backoff (max_retries).
    return LLM.LLM(api_key=config.api_key, max_retries=config.max_retries)
