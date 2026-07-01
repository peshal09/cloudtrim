"""Kubernetes manifest parser → normalized workload/service Resources (§3 Week 3).

Reads multi-document YAML (PyYAML) and correlates related objects at parse time so
the detectors stay simple per-resource: each workload records whether an HPA targets
it; each Service records whether any workload's pod labels satisfy its selector.

Workloads carry their spec (replicas, per-container requests/limits) in
`raw["k8s"]`; pod labels become `tags` so the risk scorer's env-from-tags logic
works. Usage (CPU %) is optional and arrives via the normalizer, keyed by identifier
(the same mechanism as billing).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from engine.models import Provider, Resource, ResourceType

_WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet"}


def parse_k8s(source: str | Path) -> list[Resource]:
    text = Path(source).read_text() if _looks_like_path(source) else str(source)
    docs = [d for d in yaml.safe_load_all(text) if isinstance(d, dict)]

    # HPA targets: (namespace, kind, name) that have an autoscaler.
    hpa_targets: set[tuple[str, str, str]] = set()
    for d in docs:
        if d.get("kind") == "HorizontalPodAutoscaler":
            ns = _ns(d)
            ref = (d.get("spec") or {}).get("scaleTargetRef") or {}
            if ref.get("kind") and ref.get("name"):
                hpa_targets.add((ns, ref["kind"], ref["name"]))

    workloads = [d for d in docs if d.get("kind") in _WORKLOAD_KINDS]
    services = [d for d in docs if d.get("kind") == "Service"]

    resources: list[Resource] = []
    for d in workloads:
        resources.append(_workload_resource(d, hpa_targets))
    for d in services:
        resources.append(_service_resource(d, workloads))
    return resources


def _workload_resource(d: dict[str, Any], hpa_targets: set[tuple[str, str, str]]) -> Resource:
    kind = d["kind"]
    name = _name(d)
    ns = _ns(d)
    spec = d.get("spec") or {}
    template = spec.get("template") or {}
    pod_meta = template.get("metadata") or {}
    pod_labels = {str(k): str(v) for k, v in (pod_meta.get("labels") or {}).items()}

    containers = []
    for c in (template.get("spec") or {}).get("containers") or []:
        res = c.get("resources") or {}
        containers.append(
            {
                "name": c.get("name"),
                "requests": dict(res.get("requests") or {}),
                "limits": dict(res.get("limits") or {}),
            }
        )

    k8s = {
        "kind": kind,
        "namespace": ns,
        "name": name,
        "replicas": spec.get("replicas", 1),  # DaemonSet has none -> treated as 1
        "containers": containers,
        "has_hpa": (ns, kind, name) in hpa_targets,
        "pod_labels": pod_labels,
    }
    return Resource(
        type=ResourceType.K8S_WORKLOAD,
        provider=Provider.K8S,
        identifier=f"{kind}/{ns}/{name}",
        tags=pod_labels,
        raw={"k8s": k8s, "sources": ["config"]},
    )


def _service_resource(d: dict[str, Any], workloads: list[dict[str, Any]]) -> Resource:
    name = _name(d)
    ns = _ns(d)
    spec = d.get("spec") or {}
    selector = {str(k): str(v) for k, v in (spec.get("selector") or {}).items()}

    # Matched if some same-namespace workload's pod labels satisfy the selector.
    matched = bool(selector) and any(
        _ns(w) == ns and _selector_matches(selector, _pod_labels(w)) for w in workloads
    )
    k8s = {
        "kind": "Service",
        "namespace": ns,
        "name": name,
        "selector": selector,
        "service_type": spec.get("type", "ClusterIP"),
        "matches_workload": matched,
    }
    return Resource(
        type=ResourceType.K8S_SERVICE,
        provider=Provider.K8S,
        identifier=f"Service/{ns}/{name}",
        raw={"k8s": k8s, "sources": ["config"]},
    )


def _selector_matches(selector: dict[str, str], labels: dict[str, str]) -> bool:
    return all(labels.get(k) == v for k, v in selector.items())


def _pod_labels(workload: dict[str, Any]) -> dict[str, str]:
    template = (workload.get("spec") or {}).get("template") or {}
    return {
        str(k): str(v) for k, v in ((template.get("metadata") or {}).get("labels") or {}).items()
    }


def _name(d: dict[str, Any]) -> str:
    return (d.get("metadata") or {}).get("name", "")


def _ns(d: dict[str, Any]) -> str:
    return (d.get("metadata") or {}).get("namespace", "default")


def _looks_like_path(source: str | Path) -> bool:
    if isinstance(source, Path):
        return True
    return "\n" not in source and len(source) < 4096 and Path(source).exists()
