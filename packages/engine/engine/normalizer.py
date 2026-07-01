"""Normalizer — merge config-side (IaC) and cost-side (billing) resources into one
unified `Resource` model, keyed by identifier then tags (BLUEPRINT.md §4).

This is CloudTrim's cross-signal join: Terraform knows *what is declared*
(type, size, tags); billing knows *what it costs and how used* (monthly_cost,
utilization). Merging them is what lets a detector say "declared t3.large, billed
at 3% CPU". Config values win on conflict; billing supplies cost/utilization.

Each output resource records its origin in `raw["sources"]`:
  - ["config", "billing"] — matched across both signals
  - ["config"]            — declared in IaC, no billing row (not yet billed / unmatched)
  - ["billing"]           — in the bill but not in IaC (orphan / drift candidate)
"""

from __future__ import annotations

from engine.models import Resource, ResourceType


def normalize(
    config_resources: list[Resource],
    billing_resources: list[Resource],
    analysis_id: str | None = None,
) -> list[Resource]:
    billing_by_id = {r.identifier: r for r in billing_resources}
    billing_by_name = {r.tags["Name"]: r for r in billing_resources if r.tags.get("Name")}

    merged: list[Resource] = []
    matched_billing: set[str] = set()

    for cfg in config_resources:
        bill = billing_by_id.get(cfg.identifier)
        if bill is None and cfg.tags.get("Name"):  # secondary join by Name tag
            bill = billing_by_name.get(cfg.tags["Name"])
        if bill is not None:
            matched_billing.add(bill.identifier)
            merged.append(_merge(cfg, bill, analysis_id))
        else:
            merged.append(_tagged(cfg, analysis_id, ["config"]))

    for bill in billing_resources:
        if bill.identifier not in matched_billing:
            merged.append(_tagged(bill, analysis_id, ["billing"]))

    return merged


def _merge(cfg: Resource, bill: Resource, analysis_id: str | None) -> Resource:
    return Resource(
        analysis_id=analysis_id,
        type=cfg.type if cfg.type is not ResourceType.OTHER else bill.type,
        provider=cfg.provider,
        identifier=cfg.identifier,  # canonical: the IaC address
        region=cfg.region or bill.region,
        instance_type=cfg.instance_type or bill.instance_type,
        monthly_cost=bill.monthly_cost if bill.monthly_cost is not None else cfg.monthly_cost,
        utilization=bill.utilization if bill.utilization is not None else cfg.utilization,
        tags={**bill.tags, **cfg.tags},  # config wins on conflict
        raw={"config": cfg.raw, "billing": bill.raw, "sources": ["config", "billing"]},
    )


def _tagged(resource: Resource, analysis_id: str | None, sources: list[str]) -> Resource:
    return resource.model_copy(
        update={"analysis_id": analysis_id, "raw": {**resource.raw, "sources": sources}}
    )
