"""Detector 2 — overprovisioned RDS (BLUEPRINT.md §2)."""

from __future__ import annotations

from engine.detectors.base import DetectContext, Detector, hcl_attr_diff, make_finding
from engine.models import Finding, Resource, ResourceType, Severity
from engine.sizing import downsize


class OverprovisionedRDSDetector(Detector):
    key = "overprovisioned_rds"
    title = "Overprovisioned RDS instance"

    def detect(self, resource: Resource, ctx: DetectContext) -> list[Finding]:
        if resource.type is not ResourceType.RDS:
            return []
        cpu = resource.utilization
        # cpu == 0 -> deletion candidate (orphaned_resource), not a rightsize.
        if cpu is None or cpu <= 0 or cpu >= ctx.rds_low_cpu_pct:
            return []

        target = downsize(resource.instance_type) if resource.instance_type else None
        severity = Severity.HIGH if cpu < 10 else Severity.MEDIUM
        evidence = {
            "signal": "cpu_pct",
            "cpu_pct": cpu,
            "threshold_pct": ctx.rds_low_cpu_pct,
            "current_instance_type": resource.instance_type,
            "target_instance_type": target,
            "action": "rightsize" if target else "review",
        }
        remediation = (
            hcl_attr_diff("instance_class", resource.instance_type, target) if target else None
        )
        return [make_finding(self.key, resource, self.title, severity, evidence, remediation, 0.85)]
