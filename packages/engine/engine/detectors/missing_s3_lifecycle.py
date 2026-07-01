"""Detector 4 — S3 bucket with no lifecycle policy (BLUEPRINT.md §2).

MVP limitation: only inline lifecycle config on the bucket is detected; a separate
`aws_s3_bucket_lifecycle_configuration` resource isn't correlated yet. Savings can't
be quantified without object-age data, so this is a hygiene finding (no dollar delta).
"""

from __future__ import annotations

from engine.detectors.base import DetectContext, Detector, config_attrs, make_finding, sources
from engine.models import Finding, Resource, ResourceType, Severity

_LIFECYCLE_KEYS = ("lifecycle_rule", "lifecycle_configuration")


class MissingS3LifecycleDetector(Detector):
    key = "missing_s3_lifecycle"
    title = "S3 bucket missing a lifecycle policy"

    def detect(self, resource: Resource, ctx: DetectContext) -> list[Finding]:
        if resource.type is not ResourceType.S3:
            return []
        if "config" not in sources(resource):
            return []  # can't judge IaC hygiene on a billing-only bucket
        attrs = config_attrs(resource)
        if any(k in attrs for k in _LIFECYCLE_KEYS):
            return []

        evidence = {
            "signal": "s3_lifecycle",
            "has_lifecycle": False,
            "action": "governance",
            "note": "no transition/expiration rules; old objects accrue Standard-tier cost",
        }
        return [make_finding(self.key, resource, self.title, Severity.LOW, evidence, None, 0.7)]
