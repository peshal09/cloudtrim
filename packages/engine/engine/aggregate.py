"""Savings aggregation (BLUEPRINT.md §3 Week 2).

Turns a flat finding list into an honest analysis summary. The key move is
**deduping mutually-exclusive remediations per resource**: a single resource may
attract more than one finding (e.g. rightsize *and* delete), but you apply at most
one. Summing them would double-count savings and inflate the headline number.

Rule (deterministic): group findings by resource; the realizable savings for a
resource is the single largest finding's savings (the others are alternatives).
`realistic_monthly_savings` sums those per-resource maxima; `gross_monthly_savings`
keeps the naive sum for transparency.
"""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel

from engine.models import Finding, Resource, Severity


class Opportunity(BaseModel):
    finding_id: str
    detector: str
    resource_identifier: str
    title: str
    severity: Severity
    risk: str
    monthly_savings: float


class AnalysisAggregate(BaseModel):
    realistic_monthly_savings: float  # deduped per resource — the honest headline
    gross_monthly_savings: float  # naive sum of every finding (transparency)
    savings_by_detector: dict[str, float]
    severity_counts: dict[str, int]
    top_opportunities: list[Opportunity]


def _identifier(finding: Finding, resources_by_id: dict[str, Resource]) -> str:
    res = resources_by_id.get(finding.resource_id)
    return res.identifier if res else finding.resource_id


def aggregate(
    findings: list[Finding],
    resources: list[Resource],
    top_n: int = 5,
) -> AnalysisAggregate:
    by_id = {r.id: r for r in resources}

    # Best (max-savings) finding per resource — the realizable remediation.
    best_per_resource: dict[str, Finding] = {}
    for f in findings:
        cur = best_per_resource.get(f.resource_id)
        if cur is None or f.monthly_savings > cur.monthly_savings:
            best_per_resource[f.resource_id] = f

    realistic = round(sum(f.monthly_savings for f in best_per_resource.values()), 2)
    gross = round(sum(f.monthly_savings for f in findings), 2)

    by_detector: dict[str, float] = defaultdict(float)
    for f in findings:
        by_detector[f.detector] += f.monthly_savings
    by_detector = {k: round(v, 2) for k, v in sorted(by_detector.items())}

    severity_counts = {s.value: 0 for s in Severity}
    for f in findings:
        severity_counts[f.severity.value] += 1

    opportunities = sorted(
        (f for f in best_per_resource.values() if f.monthly_savings > 0),
        key=lambda f: -f.monthly_savings,
    )[:top_n]
    top = [
        Opportunity(
            finding_id=f.id,
            detector=f.detector,
            resource_identifier=_identifier(f, by_id),
            title=f.title,
            severity=f.severity,
            risk=f.risk.value,
            monthly_savings=f.monthly_savings,
        )
        for f in opportunities
    ]

    return AnalysisAggregate(
        realistic_monthly_savings=realistic,
        gross_monthly_savings=gross,
        savings_by_detector=by_detector,
        severity_counts=severity_counts,
        top_opportunities=top,
    )
