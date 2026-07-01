from pathlib import Path

from engine.models import Provider, ResourceType
from engine.parsers import parse_k8s

FIXTURES = Path(__file__).parent / "fixtures"


def _by_id(resources):
    return {r.identifier: r for r in resources}


def test_parses_workloads_and_services():
    by_id = _by_id(parse_k8s(FIXTURES / "sample_k8s.yaml"))
    assert set(by_id) == {
        "Deployment/default/web",
        "Deployment/default/api",
        "Service/default/web-svc",
        "Service/default/ghost-svc",
    }


def test_workload_spec_and_hpa_correlation():
    by_id = _by_id(parse_k8s(FIXTURES / "sample_k8s.yaml"))

    web = by_id["Deployment/default/web"]
    assert web.type is ResourceType.K8S_WORKLOAD
    assert web.provider is Provider.K8S
    assert web.tags == {"app": "web", "env": "prod"}  # pod labels -> tags
    k = web.raw["k8s"]
    assert k["replicas"] == 5
    assert k["has_hpa"] is False
    assert k["containers"][0]["requests"] == {"cpu": "500m", "memory": "256Mi"}
    assert k["containers"][0]["limits"] == {}  # missing limits

    api = by_id["Deployment/default/api"]
    assert api.raw["k8s"]["has_hpa"] is True  # HPA targets it
    assert api.raw["k8s"]["containers"][0]["limits"]["cpu"] == "500m"


def test_service_selector_correlation():
    by_id = _by_id(parse_k8s(FIXTURES / "sample_k8s.yaml"))
    assert by_id["Service/default/web-svc"].raw["k8s"]["matches_workload"] is True
    assert by_id["Service/default/ghost-svc"].raw["k8s"]["matches_workload"] is False


def test_accepts_raw_string():
    text = "apiVersion: apps/v1\nkind: Deployment\n" "metadata:\n  name: x\nspec:\n  replicas: 1\n"
    resources = parse_k8s(text)
    assert len(resources) == 1
    assert resources[0].identifier == "Deployment/default/x"
