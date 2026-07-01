"""Detector interface, shared context, and helpers (BLUEPRINT.md §4).

A detector is deterministic business logic: given one normalized `Resource` and a
`DetectContext` (thresholds/policy), it emits zero or more `Finding`s. Detectors
decide *what is wrong* and *severity*, and record the inputs a later stage needs:
the pricing engine reads `evidence["action"]` + instance types to fill the dollar
fields; the risk scorer sets `risk`. Detectors never compute money themselves.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from engine.models import Finding, Resource, Severity


@dataclass(frozen=True)
class DetectContext:
    """Deterministic policy/thresholds. Overridable per analysis."""

    ec2_idle_cpu_pct: float = 10.0
    rds_low_cpu_pct: float = 40.0
    oversize_min_rank: int = 5  # >= "xlarge" (see engine.sizing)
    required_tags: tuple[str, ...] = ("env", "owner")


class Detector(ABC):
    key: str
    title: str

    @abstractmethod
    def detect(self, resource: Resource, ctx: DetectContext) -> list[Finding]: ...


# --- helpers shared across detectors ----------------------------------------


def sources(resource: Resource) -> list[str]:
    """Origin markers set by the normalizer: 'config' and/or 'billing'."""
    return list(resource.raw.get("sources", [])) if resource.raw else []


def config_attrs(resource: Resource) -> dict[str, Any]:
    """The IaC attributes for a resource, whether it was merged or config-only."""
    raw = resource.raw or {}
    cfg = raw.get("config", raw)
    if isinstance(cfg, dict):
        attrs = cfg.get("attrs") or cfg.get("values")
        if isinstance(attrs, dict):
            return attrs
    return {}


def hcl_attr_diff(attr: str, old: str, new: str) -> str:
    """A minimal one-attribute HCL diff. Week 4 replaces this with real codegen."""
    return f'-  {attr} = "{old}"\n+  {attr} = "{new}"'


def make_finding(
    detector: str,
    resource: Resource,
    title: str,
    severity: Severity,
    evidence: dict[str, Any],
    remediation: str | None = None,
    confidence: float = 1.0,
) -> Finding:
    # Deterministic id keeps findings stable across runs (eval + caching).
    return Finding(
        id=f"{detector}:{resource.identifier}",
        analysis_id=resource.analysis_id,
        resource_id=resource.id,
        detector=detector,
        title=title,
        severity=severity,
        evidence=evidence,
        remediation_diff=remediation,
        confidence=confidence,
    )
