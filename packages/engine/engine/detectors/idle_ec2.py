"""Detector 1 — idle / underutilized EC2 (BLUEPRINT.md §2)."""

from __future__ import annotations

from engine.detectors.base import DetectContext, Detector, hcl_attr_diff, make_finding
from engine.models import Finding, Resource, ResourceType, Severity
from engine.sizing import downsize


class IdleEC2Detector(Detector):
    key = "idle_ec2"
    title = "Idle / underutilized EC2 instance"

    def detect(self, resource: Resource, ctx: DetectContext) -> list[Finding]:
        if resource.type is not ResourceType.EC2:
            return []
        cpu = resource.utilization
        if cpu is None or cpu >= ctx.ec2_idle_cpu_pct:
            return []

        target = downsize(resource.instance_type) if resource.instance_type else None
        severity = Severity.HIGH if cpu < ctx.ec2_idle_cpu_pct / 2 else Severity.MEDIUM
        evidence = {
            "signal": "cpu_pct",
            "cpu_pct": cpu,
            "threshold_pct": ctx.ec2_idle_cpu_pct,
            "current_instance_type": resource.instance_type,
            "target_instance_type": target,
            "action": "rightsize" if target else "review",
        }
        remediation = (
            hcl_attr_diff("instance_type", resource.instance_type, target) if target else None
        )
        return [make_finding(self.key, resource, self.title, severity, evidence, remediation, 0.9)]
