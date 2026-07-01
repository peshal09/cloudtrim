"""Analysis pipeline — compose the deterministic engine end to end (BLUEPRINT.md §4).

    parse -> normalize -> detect -> price -> risk-score  [-> explain]

The explainer is injected (the engine never imports the AI layer — the one law's
dependency direction). In Week 3 this same function runs inside a worker job.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from engine.aggregate import AnalysisAggregate, aggregate
from engine.detectors import DetectContext, run_detectors
from engine.models import Analysis, AnalysisStatus, Finding, Resource
from engine.normalizer import normalize
from engine.parsers import parse_billing, parse_k8s, parse_terraform
from engine.pricing import apply_pricing
from engine.pricing.client import PricingClient
from engine.risk import apply_risk

Explainer = Callable[[Finding, Resource | None], None]


@dataclass
class AnalysisResult:
    analysis: Analysis
    resources: list[Resource]
    findings: list[Finding]
    aggregate: AnalysisAggregate


def pending_result(analysis_id: str, source_meta: dict | None = None) -> AnalysisResult:
    """A queued/not-yet-run analysis, persisted so the client can poll for status."""
    return AnalysisResult(
        analysis=Analysis(
            id=analysis_id,
            status=AnalysisStatus.PENDING,
            source_meta=dict(source_meta or {}),
        ),
        resources=[],
        findings=[],
        aggregate=aggregate([], []),
    )


def analyze(
    terraform_source: str | None = None,
    billing_source: str | None = None,
    kubernetes_source: str | None = None,
    analysis_id: str | None = None,
    ctx: DetectContext | None = None,
    pricing_client: PricingClient | None = None,
    explain: Explainer | None = None,
    source_meta: dict | None = None,
) -> AnalysisResult:
    analysis = Analysis(status=AnalysisStatus.RUNNING, source_meta=dict(source_meta or {}))
    if analysis_id is not None:
        analysis.id = analysis_id

    config: list[Resource] = []
    if terraform_source:
        config += parse_terraform(terraform_source)
    if kubernetes_source:
        config += parse_k8s(kubernetes_source)
    billing = parse_billing(billing_source) if billing_source else []
    resources = normalize(config, billing, analysis.id)

    findings = run_detectors(resources, ctx)
    apply_pricing(findings, resources, client=pricing_client)
    apply_risk(findings, resources)

    if explain is not None:
        by_id = {r.id: r for r in resources}
        for finding in findings:
            explain(finding, by_id.get(finding.resource_id))

    agg = aggregate(findings, resources)
    # Honest headline: the deduped, realizable total (not the naive sum).
    analysis.total_monthly_savings = agg.realistic_monthly_savings
    analysis.source_meta.update(
        {
            "config_resources": len(config),
            "billing_resources": len(billing),
            "resources": len(resources),
            "findings": len(findings),
        }
    )
    analysis.status = AnalysisStatus.COMPLETE
    return AnalysisResult(analysis=analysis, resources=resources, findings=findings, aggregate=agg)
