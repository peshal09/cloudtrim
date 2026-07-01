from pathlib import Path

from engine.detectors import DetectContext, run_detectors
from engine.detectors.k8s import (
    MissingHPADetector,
    MissingLimitsDetector,
    OverRequestDetector,
    ReplicaOverProvisionedDetector,
    UnusedServiceDetector,
)
from engine.models import Provider, Resource, ResourceType, Severity
from engine.parsers import parse_k8s

CTX = DetectContext()
FIXTURES = Path(__file__).parent / "fixtures"


def _wl(identifier="Deployment/default/w", **k8s):
    base = {
        "kind": "Deployment",
        "namespace": "default",
        "name": "w",
        "replicas": 1,
        "containers": [{"name": "c", "requests": {}, "limits": {}}],
        "has_hpa": False,
        "pod_labels": {"env": "prod"},
    }
    base.update(k8s)
    return Resource(
        type=ResourceType.K8S_WORKLOAD,
        provider=Provider.K8S,
        identifier=identifier,
        tags=base["pod_labels"],
        raw={"k8s": base, "sources": ["config"]},
    )


def test_missing_limits_fires_per_container():
    r = _wl(containers=[{"name": "c", "requests": {"cpu": "500m"}, "limits": {}}])
    (f,) = MissingLimitsDetector().detect(r, CTX)
    assert f.evidence["containers_missing_limits"] == ["c"]
    assert f.monthly_savings == 0.0  # hygiene, not priced


def test_missing_limits_silent_when_present():
    r = _wl(containers=[{"name": "c", "requests": {}, "limits": {"cpu": "1"}}])
    assert MissingLimitsDetector().detect(r, CTX) == []


def test_over_request_fires_on_low_usage():
    r = _wl(containers=[{"name": "c", "requests": {"cpu": "500m"}, "limits": {}}])
    r.utilization = 8.0  # from a usage merge
    (f,) = OverRequestDetector().detect(r, CTX)
    assert f.evidence["action"] == "review"
    assert f.evidence["cpu_pct"] == 8.0


def test_over_request_silent_without_usage():
    r = _wl(containers=[{"name": "c", "requests": {"cpu": "500m"}, "limits": {}}])
    assert OverRequestDetector().detect(r, CTX) == []  # no utilization signal


def test_replica_overprovisioned_fires_high_no_hpa():
    (f,) = ReplicaOverProvisionedDetector().detect(_wl(replicas=6, has_hpa=False), CTX)
    assert f.evidence["replicas"] == 6
    assert f.severity is Severity.MEDIUM


def test_replica_overprovisioned_silent_with_hpa():
    assert ReplicaOverProvisionedDetector().detect(_wl(replicas=6, has_hpa=True), CTX) == []


def test_missing_hpa_moderate_replicas_only():
    assert MissingHPADetector().detect(_wl(replicas=3, has_hpa=False), CTX)  # fires
    # high replicas belong to the replica detector, not this one
    assert MissingHPADetector().detect(_wl(replicas=6, has_hpa=False), CTX) == []
    assert MissingHPADetector().detect(_wl(replicas=1, has_hpa=False), CTX) == []


def test_unused_service():
    matched = Resource(
        type=ResourceType.K8S_SERVICE,
        identifier="Service/default/a",
        raw={"k8s": {"matches_workload": True, "selector": {"app": "a"}}, "sources": ["config"]},
    )
    orphan = Resource(
        type=ResourceType.K8S_SERVICE,
        identifier="Service/default/b",
        raw={"k8s": {"matches_workload": False, "selector": {"app": "b"}}, "sources": ["config"]},
    )
    assert UnusedServiceDetector().detect(matched, CTX) == []
    (f,) = UnusedServiceDetector().detect(orphan, CTX)
    assert f.severity is Severity.LOW


def test_registry_over_parsed_manifest():
    resources = parse_k8s(FIXTURES / "sample_k8s.yaml")
    findings = run_detectors(resources, CTX)
    keys = {(f.detector, f.id.split(":", 1)[1]) for f in findings}
    assert ("k8s_missing_limits", "Deployment/default/web") in keys
    assert ("k8s_replica_overprovisioned", "Deployment/default/web") in keys
    assert ("k8s_unused_service", "Service/default/ghost-svc") in keys
    # api is well-configured (HPA + limits) -> no findings on it
    assert not any(k[1] == "Deployment/default/api" for k in keys)
