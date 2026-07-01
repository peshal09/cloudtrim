"""End-to-end happy path through the API (sync mode), and a queue load smoke test
(BLUEPRINT.md §3 Week 5)."""

import fakeredis
import pytest
from api.jobs import enqueue_analysis, get_queue
from api.main import app
from api.sample_data import SAMPLE_CSV, SAMPLE_K8S, SAMPLE_TF
from api.settings import settings
from api.store import store
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear():
    store.clear()
    yield
    store.clear()


def test_upload_to_report_happy_path():
    files = {
        "terraform": ("main.tf", SAMPLE_TF, "text/plain"),
        "billing": ("costs.csv", SAMPLE_CSV, "text/csv"),
        "kubernetes": ("k8s.yaml", SAMPLE_K8S, "application/yaml"),
    }
    created = client.post("/api/v1/analyses", files=files)
    assert created.status_code == 201
    aid = created.json()["id"]
    assert created.json()["status"] == "complete"

    # status
    assert client.get(f"/api/v1/analyses/{aid}").json()["total_monthly_savings"] == 494.50

    # findings (sorted, top has a real patch)
    findings = client.get(f"/api/v1/analyses/{aid}/findings").json()
    assert len(findings) == 9
    top = findings[0]
    assert top["monthly_savings"] == 248.20
    assert "c5.2xlarge" in (top["remediation_diff"] or "")

    # summary + narrative
    summary = client.get(f"/api/v1/analyses/{aid}/summary").json()
    assert summary["realistic_monthly_savings"] == 494.50
    narrative = client.get(f"/api/v1/analyses/{aid}/narrative").json()
    assert "$494.50" in narrative["text"]

    # finding detail
    detail = client.get(f"/api/v1/findings/{top['id']}").json()
    assert detail["resource"]["identifier"] == "aws_instance.batch"

    # report
    md = client.get(f"/api/v1/analyses/{aid}/report.md")
    assert md.status_code == 200 and "# CloudTrim Report" in md.text


def test_queue_processes_a_batch(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'load.db'}")
    from api.store import make_store

    make_store()  # create tables
    queue = get_queue(connection=fakeredis.FakeStrictRedis(), is_async=False)

    for i in range(20):
        enqueue_analysis(queue, f"job-{i}", SAMPLE_TF, SAMPLE_CSV, None, {})

    repo = make_store()
    completed = [repo.get(f"job-{i}") for i in range(20)]
    assert all(r is not None and r.analysis.status.value == "complete" for r in completed)
    assert len(repo.trend(limit=100)) == 20
