import pytest
from api.main import app
from api.security import reset_rate_limit
from api.settings import settings
from api.store import store
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean():
    store.clear()
    reset_rate_limit()
    yield
    store.clear()
    reset_rate_limit()


def test_open_by_default_no_key_required():
    # api_keys unset -> open (the demo path)
    assert client.post("/api/v1/analyses/sample").status_code == 201


def test_api_key_enforced_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "api_keys", "secret-key")
    assert client.post("/api/v1/analyses/sample").status_code == 401
    ok = client.post("/api/v1/analyses/sample", headers={"Authorization": "Bearer secret-key"})
    assert ok.status_code == 201
    xkey = client.post("/api/v1/analyses/sample", headers={"X-API-Key": "secret-key"})
    assert xkey.status_code == 201
    assert client.post("/api/v1/analyses/sample", headers={"X-API-Key": "wrong"}).status_code == 401


def test_rate_limit_enforced_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 2)
    assert client.get("/api/v1/trends").status_code == 200
    assert client.get("/api/v1/trends").status_code == 200
    assert client.get("/api/v1/trends").status_code == 429  # third within the minute


def test_health_and_metrics_are_unprotected(monkeypatch):
    monkeypatch.setattr(settings, "api_keys", "secret-key")
    assert client.get("/api/v1/healthz").status_code == 200
    assert client.get("/metrics").status_code == 200
