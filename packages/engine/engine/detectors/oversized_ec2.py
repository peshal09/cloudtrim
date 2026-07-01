"""Detector 3 — oversized EC2 declared in IaC with no runtime signal (BLUEPRINT.md §2).

Complements idle_ec2: fires on config-side smell (a large instance declared in
Terraform) when there is *no* utilization data to prove it's needed. When billing
utilization exists, idle_ec2 owns the call instead.
"""

from __future__ import annotations

from engine.detectors.base import (
    DetectContext,
    Detector,
    hcl_attr_diff,
    make_finding,
    sources,
)
from engine.models import Finding, Resource, ResourceType, Severity
from engine.sizing import downsize, size_rank


class OversizedEC2Detector(Detector):
    key = "oversized_ec2"
    title = "Oversized EC2 declared in Terraform"

    def detect(self, resource: Resource, ctx: DetectContext) -> list[Finding]:
        if resource.type is not ResourceType.EC2:
            return []
        if resource.utilization is not None:
            return []  # have a runtime signal -> idle_ec2's job
        if "config" not in sources(resource) or not resource.instance_type:
            return []
        rank = size_rank(resource.instance_type)
        if rank < ctx.oversize_min_rank:
            return []

        target = downsize(resource.instance_type)
        severity = Severity.MEDIUM if rank >= 6 else Severity.LOW  # >= 2xlarge
        evidence = {
            "signal": "declared_size",
            "current_instance_type": resource.instance_type,
            "target_instance_type": target,
            "size_rank": rank,
            "action": "rightsize" if target else "review",
            "note": "large instance declared in IaC with no utilization data to justify it",
        }
        remediation = (
            hcl_attr_diff("instance_type", resource.instance_type, target) if target else None
        )
        return [make_finding(self.key, resource, self.title, severity, evidence, remediation, 0.6)]
