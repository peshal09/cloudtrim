from engine.detectors import DetectContext, run_detectors
from engine.detectors.governance import GovernanceDetector
from engine.detectors.idle_ec2 import IdleEC2Detector
from engine.detectors.missing_s3_lifecycle import MissingS3LifecycleDetector
from engine.detectors.orphaned_resource import OrphanedResourceDetector
from engine.detectors.overprovisioned_rds import OverprovisionedRDSDetector
from engine.detectors.oversized_ec2 import OversizedEC2Detector
from engine.models import Resource, ResourceType, Severity

CTX = DetectContext()


def _ec2(**kw):
    kw.setdefault("raw", {"sources": ["config", "billing"]})
    return Resource(type=ResourceType.EC2, **kw)


# --- idle_ec2 ----------------------------------------------------------------


def test_idle_ec2_fires_high_and_proposes_downsize():
    r = _ec2(identifier="aws_instance.web", instance_type="t3.large", utilization=3.0)
    (f,) = IdleEC2Detector().detect(r, CTX)
    assert f.detector == "idle_ec2"
    assert f.severity is Severity.HIGH  # 3% < threshold/2
    assert f.evidence["target_instance_type"] == "t3.medium"
    assert f.evidence["action"] == "rightsize"
    assert "t3.medium" in f.remediation_diff


def test_idle_ec2_silent_when_utilized():
    r = _ec2(identifier="aws_instance.web", instance_type="t3.large", utilization=55.0)
    assert IdleEC2Detector().detect(r, CTX) == []


# --- overprovisioned_rds -----------------------------------------------------


def test_overprovisioned_rds_downsizes_db_class():
    r = Resource(
        type=ResourceType.RDS,
        identifier="aws_db_instance.main",
        instance_type="db.t3.medium",
        utilization=20.0,
        raw={"sources": ["config", "billing"]},
    )
    (f,) = OverprovisionedRDSDetector().detect(r, CTX)
    assert f.evidence["target_instance_type"] == "db.t3.small"
    assert f.severity is Severity.MEDIUM


# --- oversized_ec2 -----------------------------------------------------------


def test_oversized_ec2_fires_on_config_only_large_instance():
    r = _ec2(
        identifier="aws_instance.big",
        instance_type="c5.2xlarge",
        raw={"sources": ["config"], "attrs": {}},
    )
    (f,) = OversizedEC2Detector().detect(r, CTX)
    assert f.evidence["target_instance_type"] == "c5.xlarge"
    assert f.severity is Severity.MEDIUM  # >= 2xlarge


def test_oversized_ec2_defers_when_utilization_known():
    r = _ec2(identifier="aws_instance.big", instance_type="c5.2xlarge", utilization=1.0)
    assert OversizedEC2Detector().detect(r, CTX) == []  # idle_ec2 owns this


# --- missing_s3_lifecycle ----------------------------------------------------


def test_missing_s3_lifecycle_fires_without_rule():
    r = Resource(
        type=ResourceType.S3,
        identifier="aws_s3_bucket.logs",
        raw={"sources": ["config"], "attrs": {"bucket": "logs"}},
    )
    (f,) = MissingS3LifecycleDetector().detect(r, CTX)
    assert f.evidence["has_lifecycle"] is False


def test_missing_s3_lifecycle_silent_with_rule():
    r = Resource(
        type=ResourceType.S3,
        identifier="aws_s3_bucket.logs",
        raw={"sources": ["config"], "attrs": {"lifecycle_rule": {"enabled": True}}},
    )
    assert MissingS3LifecycleDetector().detect(r, CTX) == []


# --- governance --------------------------------------------------------------


def test_governance_flags_hardcoded_region_and_missing_owner_tag():
    r = _ec2(
        identifier="aws_instance.web",
        tags={"env": "prod"},
        raw={"sources": ["config"], "attrs": {"region": "us-east-1"}},
    )
    (f,) = GovernanceDetector().detect(r, CTX)
    assert f.evidence["hardcoded_region"] == "us-east-1"
    assert f.evidence["missing_tags"] == ["owner"]
    assert len(f.evidence["issues"]) == 2


def test_governance_silent_when_interpolated_region_and_tags_present():
    r = _ec2(
        identifier="aws_instance.web",
        tags={"env": "prod", "owner": "team-a"},
        raw={"sources": ["config"], "attrs": {"region": "${var.region}"}},
    )
    assert GovernanceDetector().detect(r, CTX) == []


# --- orphaned_resource -------------------------------------------------------


def test_orphaned_resource_in_bill_not_iac():
    r = _ec2(identifier="i-0abc", monthly_cost=30.0, utilization=12.0, raw={"sources": ["billing"]})
    (f,) = OrphanedResourceDetector().detect(r, CTX)
    assert f.severity is Severity.HIGH
    assert f.evidence["action"] == "delete"


def test_orphaned_resource_zero_util_with_cost():
    r = _ec2(identifier="aws_instance.z", monthly_cost=20.0, utilization=0.0)
    (f,) = OrphanedResourceDetector().detect(r, CTX)
    assert "zero utilization" in f.evidence["reason"]


# --- registry ----------------------------------------------------------------


def test_registry_runs_all_detectors_over_a_mixed_fleet():
    fleet = [
        _ec2(
            identifier="aws_instance.web",
            instance_type="t3.large",
            utilization=3.0,
            tags={"env": "prod", "owner": "x"},
            raw={"sources": ["config", "billing"]},
        ),
        Resource(
            type=ResourceType.S3,
            identifier="aws_s3_bucket.logs",
            tags={"env": "prod", "owner": "x"},
            raw={"sources": ["config"], "attrs": {}},
        ),
        _ec2(
            identifier="i-0orphan", monthly_cost=30.0, utilization=0.0, raw={"sources": ["billing"]}
        ),
    ]
    findings = run_detectors(fleet, CTX)
    keys = {f.detector for f in findings}
    assert {"idle_ec2", "missing_s3_lifecycle", "orphaned_resource"} <= keys
    # deterministic ids: detector:identifier, unique
    assert len({f.id for f in findings}) == len(findings)
