from api.main import app
from api.observability import metrics
from fastapi.testclient import TestClient

client = TestClient(app)


def test_request_id_header_present():
    resp = client.get("/api/v1/healthz")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")


def test_request_id_is_propagated_when_supplied():
    resp = client.get("/api/v1/healthz", headers={"X-Request-ID": "abc-123"})
    assert resp.headers["X-Request-ID"] == "abc-123"


def test_error_envelope_has_taxonomy_and_request_id():
    resp = client.get("/api/v1/analyses/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["type"] == "not_found"
    assert body["error"]["request_id"]
    assert body["detail"] == "analysis not found"  # back-compat field


def test_metrics_endpoint_exposes_prometheus_counters():
    metrics.reset()
    client.get("/api/v1/healthz")
    text = client.get("/metrics").text
    assert "cloudtrim_http_requests_total" in text
    # the matched route template is the label, not the raw path (low cardinality)
    assert 'path="/healthz"' in text
    assert "cloudtrim_http_request_duration_seconds_sum" in text
