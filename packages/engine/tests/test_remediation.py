from engine.models import Finding, Risk, Severity
from engine.remediation import (
    generate_tf_patch,
    rewrite_k8s,
    rewrite_tf,
    validate_hcl,
    validate_yaml,
)

TF = """resource "aws_instance" "web" {
  instance_type = "t3.xlarge"
  tags = {
    env  = "prod"
    Name = "web"
  }
}

resource "aws_db_instance" "main" {
  instance_class = "db.m5.xlarge"
}
"""

K8S = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: default
spec:
  replicas: 6
  template:
    spec:
      containers:
        - name: web
"""


def _finding(finding_id, detector, action, **evidence):
    return Finding(
        id=finding_id,
        resource_id="r",
        detector=detector,
        title="t",
        severity=Severity.HIGH,
        risk=Risk.MEDIUM,
        evidence={"action": action, **evidence},
    )


def test_rewrite_tf_rightsizes_ec2_and_stays_valid():
    f = _finding(
        "idle_ec2:aws_instance.web",
        "idle_ec2",
        "rightsize",
        current_instance_type="t3.xlarge",
        target_instance_type="t3.large",
    )
    patched = rewrite_tf(f, TF)
    assert patched is not None
    assert 'instance_type = "t3.large"' in patched
    assert "t3.xlarge" not in patched  # the only occurrence was replaced
    assert "tags = {" in patched  # nested block untouched (brace-depth aware)
    assert validate_hcl(patched)  # still parses


def test_rewrite_tf_rds_uses_instance_class():
    f = _finding(
        "overprovisioned_rds:aws_db_instance.main",
        "overprovisioned_rds",
        "rightsize",
        current_instance_type="db.m5.xlarge",
        target_instance_type="db.m5.large",
    )
    patched = rewrite_tf(f, TF)
    assert 'instance_class = "db.m5.large"' in patched


def test_tf_patch_is_a_unified_diff():
    f = _finding(
        "idle_ec2:aws_instance.web",
        "idle_ec2",
        "rightsize",
        current_instance_type="t3.xlarge",
        target_instance_type="t3.large",
    )
    diff = generate_tf_patch(f, TF)
    assert diff.startswith("--- a/")
    assert '-  instance_type = "t3.xlarge"' in diff
    assert '+  instance_type = "t3.large"' in diff


def test_non_rightsize_finding_has_no_patch():
    f = _finding("governance:aws_instance.web", "governance", "governance")
    assert rewrite_tf(f, TF) is None
    assert generate_tf_patch(f, TF) is None


def test_rewrite_k8s_reduces_replicas_and_stays_valid():
    f = _finding(
        "k8s_replica_overprovisioned:Deployment/default/web",
        "k8s_replica_overprovisioned",
        "review",
        replicas=6,
    )
    patched = rewrite_k8s(f, K8S)
    assert patched is not None
    assert "replicas: 3" in patched
    assert "replicas: 6" not in patched
    assert validate_yaml(patched)
