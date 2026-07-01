"""Kubernetes detectors (BLUEPRINT.md §2/§3 Week 3).

Five config-side workload anti-patterns. These are hygiene findings: we report the
issue and the reclaimable resources in evidence, but we do NOT price them — there's
no honest node-cost model yet, and the one law forbids fabricating a dollar figure
(node-cost attribution is a later stretch). Severity conveys importance; savings
stay $0.

Actions: "governance" (safe hygiene -> LOW risk) for missing limits / missing HPA /
unused Service; "review" (a tuning change with availability implications, risk-scored
normally) for over-request and replica over-provisioning.
"""

from __future__ import annotations

from engine.detectors.base import DetectContext, Detector, make_finding
from engine.models import Finding, Resource, ResourceType, Severity


def _k8s(resource: Resource) -> dict:
    return resource.raw.get("k8s", {}) if resource.raw else {}


class MissingLimitsDetector(Detector):
    key = "k8s_missing_limits"
    title = "Container missing resource limits"

    def detect(self, resource: Resource, ctx: DetectContext) -> list[Finding]:
        if resource.type is not ResourceType.K8S_WORKLOAD:
            return []
        k = _k8s(resource)
        missing = [c.get("name") for c in k.get("containers", []) if not c.get("limits")]
        if not missing:
            return []
        evidence = {
            "signal": "k8s_limits",
            "containers_missing_limits": missing,
            "action": "governance",
            "note": (
                f"containers without CPU/memory limits: {', '.join(missing)} — "
                "unbounded pods can starve neighbors on the node"
            ),
        }
        return [make_finding(self.key, resource, self.title, Severity.MEDIUM, evidence, None, 0.9)]


class OverRequestDetector(Detector):
    key = "k8s_over_request"
    title = "Over-requested CPU vs usage"

    def detect(self, resource: Resource, ctx: DetectContext) -> list[Finding]:
        if resource.type is not ResourceType.K8S_WORKLOAD:
            return []
        cpu = resource.utilization
        if cpu is None or cpu <= 0 or cpu >= ctx.k8s_over_request_cpu_pct:
            return []
        k = _k8s(resource)
        if not any(c.get("requests", {}).get("cpu") for c in k.get("containers", [])):
            return []
        evidence = {
            "signal": "k8s_request",
            "cpu_pct": cpu,
            "threshold_pct": ctx.k8s_over_request_cpu_pct,
            "action": "review",
            "note": (
                f"pods average {cpu}% CPU against their requests — the CPU request "
                "looks oversized; lower it to improve bin-packing"
            ),
        }
        return [make_finding(self.key, resource, self.title, Severity.MEDIUM, evidence, None, 0.7)]


class ReplicaOverProvisionedDetector(Detector):
    key = "k8s_replica_overprovisioned"
    title = "Replica over-provisioning (no autoscaling)"

    def detect(self, resource: Resource, ctx: DetectContext) -> list[Finding]:
        if resource.type is not ResourceType.K8S_WORKLOAD:
            return []
        k = _k8s(resource)
        if k.get("kind") == "DaemonSet" or k.get("has_hpa"):
            return []
        replicas = k.get("replicas", 1)
        if replicas < ctx.k8s_high_replicas:
            return []
        evidence = {
            "signal": "k8s_replicas",
            "replicas": replicas,
            "has_hpa": False,
            "action": "review",
            "note": (
                f"{replicas} fixed replicas with no HorizontalPodAutoscaler — likely "
                "over-provisioned; add autoscaling to scale to actual demand"
            ),
        }
        return [make_finding(self.key, resource, self.title, Severity.MEDIUM, evidence, None, 0.7)]


class MissingHPADetector(Detector):
    key = "k8s_missing_hpa"
    title = "Missing HorizontalPodAutoscaler"

    def detect(self, resource: Resource, ctx: DetectContext) -> list[Finding]:
        if resource.type is not ResourceType.K8S_WORKLOAD:
            return []
        k = _k8s(resource)
        if k.get("kind") not in ("Deployment", "StatefulSet") or k.get("has_hpa"):
            return []
        replicas = k.get("replicas", 1)
        # >= high-replica threshold is covered by ReplicaOverProvisioned (avoid overlap).
        if replicas < 2 or replicas >= ctx.k8s_high_replicas:
            return []
        evidence = {
            "signal": "k8s_hpa",
            "replicas": replicas,
            "action": "governance",
            "note": "no HorizontalPodAutoscaler — scaling is manual and won't track demand",
        }
        return [make_finding(self.key, resource, self.title, Severity.LOW, evidence, None, 0.6)]


class UnusedServiceDetector(Detector):
    key = "k8s_unused_service"
    title = "Unused Service (selector matches nothing)"

    def detect(self, resource: Resource, ctx: DetectContext) -> list[Finding]:
        if resource.type is not ResourceType.K8S_SERVICE:
            return []
        k = _k8s(resource)
        if k.get("matches_workload"):
            return []
        evidence = {
            "signal": "k8s_service",
            "selector": k.get("selector", {}),
            "action": "governance",
            "note": "Service selector matches no workload in its namespace — orphaned",
        }
        return [make_finding(self.key, resource, self.title, Severity.LOW, evidence, None, 0.75)]
