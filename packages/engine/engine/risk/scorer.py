"""Deterministic risk scorer (BLUEPRINT.md §2/§3-Week2).

Rollout risk = "how dangerous is applying this remediation", scored Low/Med/High
from four deterministic signals:

  - reversibility (the action): deleting is irreversible (data loss); rightsizing
    is reversible; a governance/tagging change is safe.
  - statefulness (the resource): RDS/S3/EBS hold data; EC2 compute is replaceable.
  - blast radius (the environment, from tags): prod > staging > dev.

No LLM, no dollars — a separate axis from severity. The factor breakdown is written
back to `evidence["risk_factors"]` so the UI and the explainer can show *why*.
"""

from __future__ import annotations

from typing import Any

from engine.models import Finding, Resource, ResourceType, Risk

_STATEFUL = {ResourceType.RDS, ResourceType.S3, ResourceType.EBS}
_ENV_KEYS = ("env", "environment")
_ENV_POINTS = {"prod": 2, "staging": 1, "dev": 0}


def score_risk(finding: Finding, resource: Resource | None) -> tuple[Risk, dict[str, Any]]:
    action = finding.evidence.get("action")

    # A tagging / lifecycle governance change is safe and reversible by construction.
    if action == "governance":
        return Risk.LOW, {"reason": "governance change is safe and reversible", "score": 0}

    points = 0
    factors: dict[str, Any] = {}

    if action == "delete":
        points += 2
        factors["reversibility"] = "delete (irreversible, possible data loss): +2"
    else:  # rightsize / review
        points += 1
        factors["reversibility"] = f"{action or 'change'} (reversible): +1"

    if resource is not None and resource.type in _STATEFUL:
        points += 2
        factors["statefulness"] = f"{resource.type} is stateful: +2"
    else:
        factors["statefulness"] = "stateless/compute: +0"

    env = _environment(resource)
    env_points = _ENV_POINTS.get(env, 1)  # unknown env is treated as slightly risky
    points += env_points
    factors["blast_radius"] = f"env={env or 'unknown'}: +{env_points}"

    factors["score"] = points
    risk = Risk.HIGH if points >= 4 else Risk.MEDIUM if points >= 2 else Risk.LOW
    return risk, factors


def apply_risk(findings: list[Finding], resources: list[Resource]) -> list[Finding]:
    by_id = {r.id: r for r in resources}
    for finding in findings:
        risk, factors = score_risk(finding, by_id.get(finding.resource_id))
        finding.risk = risk
        finding.evidence["risk_factors"] = factors
    return findings


def _environment(resource: Resource | None) -> str | None:
    if resource is None:
        return None
    for key, value in resource.tags.items():
        if key.lower() in _ENV_KEYS:
            v = value.lower()
            if v.startswith("prod"):
                return "prod"
            if v.startswith(("stag", "stg")):
                return "staging"
            if v.startswith(("dev", "test", "qa")):
                return "dev"
    return None
