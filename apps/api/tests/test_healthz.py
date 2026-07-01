from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_healthz_returns_ok():
    resp = client.get("/api/v1/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
