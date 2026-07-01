import pytest
from api.main import app
from api.store import store
from fastapi.testclient import TestClient

client = TestClient(app)

TF = """
resource "aws_instance" "web" {
  instance_type = "t3.large"
  tags = {
    env   = "prod"
    owner = "team-a"
  }
}
"""

CSV = """identifier,service,region,instance_type,monthly_cost,cpu_utilization
aws_instance.web,ec2,us-east-1,t3.large,60.74,3.0
"""


@pytest.fixture(autouse=True)
def _clear_store():
    store.clear()
    yield
    store.clear()


def _upload(tf=TF, csv=CSV):
    files = {"terraform": ("main.tf", tf, "text/plain")}
    if csv is not None:
        files["billing"] = ("costs.csv", csv, "text/csv")
    return client.post("/api/v1/analyses", files=files)


def test_create_analysis_runs_engine_and_returns_summary():
    resp = _upload()
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "complete"
    assert body["findings_count"] >= 1
    assert body["total_monthly_savings"] == 30.37  # t3.large -> t3.medium
    assert body["severity_counts"]["high"] >= 1


def test_get_analysis_roundtrip_and_404():
    analysis_id = _upload().json()["id"]
    got = client.get(f"/api/v1/analyses/{analysis_id}")
    assert got.status_code == 200
    assert got.json()["id"] == analysis_id
    assert client.get("/api/v1/analyses/nope").status_code == 404


def test_list_findings_sorted_and_priced():
    analysis_id = _upload().json()["id"]
    resp = client.get(f"/api/v1/analyses/{analysis_id}/findings")
    assert resp.status_code == 200
    findings = resp.json()
    assert findings[0]["detector"] == "idle_ec2"  # highest savings first
    assert findings[0]["monthly_savings"] == 30.37
    assert findings[0]["risk"] in {"low", "medium", "high"}
    assert "risk_factors" in findings[0]["evidence"]


def test_get_finding_detail_includes_resource():
    _upload()
    resp = client.get("/api/v1/findings/idle_ec2:aws_instance.web")
    assert resp.status_code == 200
    body = resp.json()
    assert body["finding"]["detector"] == "idle_ec2"
    assert body["resource"]["identifier"] == "aws_instance.web"
    assert client.get("/api/v1/findings/does:not-exist").status_code == 404


def test_terraform_only_upload_still_works():
    resp = _upload(csv=None)
    assert resp.status_code == 201
    assert resp.json()["status"] == "complete"  # config-only findings (no savings needed)


K8S = """
apiVersion: apps/v1
kind: Deployment
metadata: { name: web, namespace: default }
spec:
  replicas: 6
  template:
    metadata: { labels: { app: web } }
    spec:
      containers:
        - name: web
          resources: { requests: { cpu: "500m" } }
"""


def test_kubernetes_only_upload():
    files = {"kubernetes": ("k8s.yaml", K8S, "application/yaml")}
    resp = client.post("/api/v1/analyses", files=files)
    assert resp.status_code == 201
    analysis_id = resp.json()["id"]
    findings = client.get(f"/api/v1/analyses/{analysis_id}/findings").json()
    detectors = {f["detector"] for f in findings}
    assert "k8s_missing_limits" in detectors
    assert "k8s_replica_overprovisioned" in detectors


def test_upload_requires_at_least_one_file():
    assert client.post("/api/v1/analyses", files={}).status_code == 400
