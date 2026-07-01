import pytest
from api.main import app
from api.store import store
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_store():
    store.clear()
    yield
    store.clear()


def test_sample_endpoint_runs_the_demo_dataset():
    resp = client.post("/api/v1/analyses/sample")
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_meta"]["sample"] is True
    # Deterministic demo total (matches the eval harness).
    assert body["total_monthly_savings"] == 494.50  # deduped; K8s findings are $0
    assert body["findings_count"] == 9  # 6 AWS + 3 Kubernetes


def test_summary_endpoint_returns_aggregate():
    analysis_id = client.post("/api/v1/analyses/sample").json()["id"]
    summary = client.get(f"/api/v1/analyses/{analysis_id}/summary").json()
    # Demo has no overlapping remediations, so realistic == gross.
    assert summary["realistic_monthly_savings"] == 494.50
    assert summary["gross_monthly_savings"] == 494.50
    assert summary["top_opportunities"][0]["detector"] == "oversized_ec2"
    assert summary["savings_by_detector"]["overprovisioned_rds"] == 124.83


def test_narrative_endpoint_prioritizes_via_template():
    analysis_id = client.post("/api/v1/analyses/sample").json()["id"]
    n = client.get(f"/api/v1/analyses/{analysis_id}/narrative").json()
    assert n["source"] == "template"
    assert "aws_instance.batch" in n["text"]  # highest-savings opportunity
    assert "$494.50" in n["text"]


def test_sample_findings_are_explained_via_template():
    analysis_id = client.post("/api/v1/analyses/sample").json()["id"]
    findings = client.get(f"/api/v1/analyses/{analysis_id}/findings").json()
    top = findings[0]
    assert top["detector"] == "oversized_ec2"  # highest single savings ($248.20)
    assert top["explanation_source"] == "template"
    assert top["explanation"]
