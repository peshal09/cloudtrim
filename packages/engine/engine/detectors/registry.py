"""Detector registry + runner (BLUEPRINT.md §4).

Registering a new detector = add its class here. The runner applies every detector
to every resource and flattens the findings.
"""

from __future__ import annotations

from engine.detectors.base import DetectContext, Detector
from engine.detectors.governance import GovernanceDetector
from engine.detectors.idle_ec2 import IdleEC2Detector
from engine.detectors.k8s import (
    MissingHPADetector,
    MissingLimitsDetector,
    OverRequestDetector,
    ReplicaOverProvisionedDetector,
    UnusedServiceDetector,
)
from engine.detectors.missing_s3_lifecycle import MissingS3LifecycleDetector
from engine.detectors.orphaned_resource import OrphanedResourceDetector
from engine.detectors.overprovisioned_rds import OverprovisionedRDSDetector
from engine.detectors.oversized_ec2 import OversizedEC2Detector
from engine.models import Finding, Resource

DETECTORS: list[Detector] = [
    # AWS / IaC
    IdleEC2Detector(),
    OverprovisionedRDSDetector(),
    OversizedEC2Detector(),
    MissingS3LifecycleDetector(),
    GovernanceDetector(),
    OrphanedResourceDetector(),
    # Kubernetes
    MissingLimitsDetector(),
    OverRequestDetector(),
    ReplicaOverProvisionedDetector(),
    MissingHPADetector(),
    UnusedServiceDetector(),
]


def run_detectors(resources: list[Resource], ctx: DetectContext | None = None) -> list[Finding]:
    ctx = ctx or DetectContext()
    findings: list[Finding] = []
    for resource in resources:
        for detector in DETECTORS:
            findings.extend(detector.detect(resource, ctx))
    return findings
