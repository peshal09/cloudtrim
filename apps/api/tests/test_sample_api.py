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
    assert body["total_monthly_savings"] == 494.50
    assert body["findings_count"] == 6


def test_sample_findings_are_explained_via_template():
    analysis_id = client.post("/api/v1/analyses/sample").json()["id"]
    findings = client.get(f"/api/v1/analyses/{analysis_id}/findings").json()
    top = findings[0]
    assert top["detector"] == "oversized_ec2"  # highest single savings ($248.20)
    assert top["explanation_source"] == "template"
    assert top["explanation"]
