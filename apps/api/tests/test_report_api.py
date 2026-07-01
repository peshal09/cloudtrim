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


def _sample_id() -> str:
    return client.post("/api/v1/analyses/sample").json()["id"]


def test_markdown_report_contains_summary_narrative_and_findings():
    md = client.get(f"/api/v1/analyses/{_sample_id()}/report.md")
    assert md.status_code == 200
    assert md.headers["content-type"].startswith("text/markdown")
    body = md.text
    assert "# CloudTrim Report" in body
    assert "## Prioritization" in body
    assert "$494.50" in body  # realizable savings headline
    assert "| Detector | Resource |" in body
    assert "aws_instance.batch" in body


def test_markdown_report_404_for_unknown():
    assert client.get("/api/v1/analyses/nope/report.md").status_code == 404


def test_pdf_report_is_a_pdf():
    pytest.importorskip("fpdf")
    resp = client.get(f"/api/v1/analyses/{_sample_id()}/report.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:5] == b"%PDF-"
    assert len(resp.content) > 1000
