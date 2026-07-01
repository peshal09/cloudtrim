"""Savings computation — fill each Finding's dollar fields from the pricing engine
(BLUEPRINT.md §2/§6). This is the ONLY place a finding's money is set.

Reads the detector's `evidence["action"]`:
  - "rightsize": price(current) and price(target) -> savings = current - projected
  - "delete":    price(current) (or the billed cost) -> savings = current, projected 0
  - anything else (governance/review): left at 0 — a hygiene finding, no dollar delta

Every figure traces to the pricing engine (or, for deletions with no priced type,
the observed billing cost). The LLM never sees a number it didn't get from here.
"""

from __future__ import annotations

from engine.models import Finding, Resource
from engine.pricing.client import PricingClient


def apply_pricing(
    findings: list[Finding],
    resources: list[Resource],
    client: PricingClient | None = None,
) -> list[Finding]:
    client = client or PricingClient()
    by_id = {r.id: r for r in resources}

    for finding in findings:
        resource = by_id.get(finding.resource_id)
        region = resource.region if resource else None
        action = finding.evidence.get("action")
        current_type = finding.evidence.get("current_instance_type")
        target_type = finding.evidence.get("target_instance_type")

        if action == "rightsize":
            current = client.get_price(current_type, region)
            projected = client.get_price(target_type, region)
            if current is not None and projected is not None:
                _set(finding, current, projected)

        elif action == "delete":
            current = client.get_price(current_type, region)
            if current is None and resource is not None:
                current = resource.monthly_cost  # nothing to price -> use the bill
            if current is not None:
                _set(finding, current, 0.0)

        # governance / review / unknown -> leave zeros

    return findings


def _set(finding: Finding, current: float, projected: float) -> None:
    finding.current_cost = round(current, 2)
    finding.projected_cost = round(projected, 2)
    finding.monthly_savings = round(current - projected, 2)
