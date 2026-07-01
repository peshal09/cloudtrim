"""Detector 6 — orphaned / idle resource, a deletion candidate (BLUEPRINT.md §2).

Two signals, both meaning "you're paying for something you shouldn't be":
  - in the bill but not declared in IaC (drift / forgotten resource), or
  - zero utilization with ongoing cost.
Projected cost after deletion is $0, so the whole current cost is savings — the
pricing engine computes that from `action == "delete"`.
"""

from __future__ import annotations

from engine.detectors.base import DetectContext, Detector, make_finding, sources
from engine.models import Finding, Resource, Severity


class OrphanedResourceDetector(Detector):
    key = "orphaned_resource"
    title = "Orphaned / idle resource (deletion candidate)"

    def detect(self, resource: Resource, ctx: DetectContext) -> list[Finding]:
        srcs = sources(resource)
        in_bill_not_iac = srcs == ["billing"]
        idle_billed = resource.utilization == 0.0 and (resource.monthly_cost or 0) > 0
        if not (in_bill_not_iac or idle_billed):
            return []

        reason = (
            "present in billing but not declared in IaC"
            if in_bill_not_iac
            else "zero utilization with ongoing cost"
        )
        evidence = {
            "signal": "orphan",
            "reason": reason,
            "current_instance_type": resource.instance_type,
            "action": "delete",
        }
        return [make_finding(self.key, resource, self.title, Severity.HIGH, evidence, None, 0.75)]
