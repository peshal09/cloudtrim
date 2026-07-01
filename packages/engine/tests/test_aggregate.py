from engine.aggregate import aggregate
from engine.models import Finding, Resource, ResourceType, Risk, Severity


def _f(resource_id, detector, savings, severity=Severity.HIGH):
    return Finding(
        resource_id=resource_id,
        detector=detector,
        title=detector,
        severity=severity,
        risk=Risk.MEDIUM,
        monthly_savings=savings,
        current_cost=savings,
    )


def _r(rid, ident):
    return Resource(id=rid, identifier=ident, type=ResourceType.EC2)


def test_dedupes_mutually_exclusive_remediations_per_resource():
    # One resource with BOTH a rightsize ($30) and a delete ($60): realizable is $60,
    # not $90. A second resource adds $124.
    resources = [_r("r1", "aws_instance.web"), _r("r2", "aws_db_instance.main")]
    findings = [
        _f("r1", "idle_ec2", 30.0),
        _f("r1", "orphaned_resource", 60.0),
        _f("r2", "overprovisioned_rds", 124.0),
    ]
    agg = aggregate(findings, resources)
    assert agg.gross_monthly_savings == 214.0  # naive sum
    assert agg.realistic_monthly_savings == 184.0  # 60 (best of r1) + 124 (r2)


def test_savings_by_detector_and_severity_counts():
    resources = [_r("r1", "a"), _r("r2", "b")]
    findings = [
        _f("r1", "idle_ec2", 30.0, Severity.HIGH),
        _f("r2", "governance", 0.0, Severity.LOW),
    ]
    agg = aggregate(findings, resources)
    assert agg.savings_by_detector == {"governance": 0.0, "idle_ec2": 30.0}
    assert agg.severity_counts == {"low": 1, "medium": 0, "high": 2 - 1}


def test_top_opportunities_are_deduped_and_sorted():
    resources = [_r("r1", "aws_instance.web"), _r("r2", "aws_instance.batch")]
    findings = [
        _f("r1", "idle_ec2", 30.0),
        _f("r1", "orphaned_resource", 60.0),  # same resource, larger — wins
        _f("r2", "oversized_ec2", 45.0),
        _f("r2", "governance", 0.0),  # zero savings — excluded
    ]
    agg = aggregate(findings, resources)
    ids = [(o.resource_identifier, o.monthly_savings) for o in agg.top_opportunities]
    assert ids == [("aws_instance.web", 60.0), ("aws_instance.batch", 45.0)]
