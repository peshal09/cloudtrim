"""Detector 5 — governance anti-patterns: hardcoded region / missing tags (§2).

A hygiene finding (no dollar delta) that gates code-review quality: a literal region
pins the config to one place, and missing ownership/environment tags break cost
allocation and accountability.
"""

from __future__ import annotations

from engine.detectors.base import DetectContext, Detector, config_attrs, make_finding, sources
from engine.models import Finding, Provider, Resource, Severity


class GovernanceDetector(Detector):
    key = "governance"
    title = "Governance anti-pattern (hardcoded region / missing tags)"

    def detect(self, resource: Resource, ctx: DetectContext) -> list[Finding]:
        # AWS/IaC hygiene only — K8s workloads have their own detectors and label model.
        if resource.provider is not Provider.AWS or "config" not in sources(resource):
            return []

        attrs = config_attrs(resource)
        issues: list[str] = []

        region = attrs.get("region")
        hardcoded_region = None
        if isinstance(region, str) and region and "${" not in region:
            hardcoded_region = region
            issues.append(f"hardcoded region '{region}'")

        missing_tags = [t for t in ctx.required_tags if t not in resource.tags]
        if missing_tags:
            issues.append("missing tags: " + ", ".join(missing_tags))

        if not issues:
            return []

        evidence = {
            "signal": "governance",
            "issues": issues,
            "hardcoded_region": hardcoded_region,
            "missing_tags": missing_tags,
            "action": "governance",
        }
        return [make_finding(self.key, resource, self.title, Severity.LOW, evidence, None, 0.8)]
