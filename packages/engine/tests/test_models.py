from engine.models import (
    Analysis,
    AnalysisStatus,
    ExplanationSource,
    Finding,
    Resource,
    ResourceType,
    Risk,
    Severity,
)


def test_resource_defaults_and_required_identifier():
    r = Resource(identifier="aws_instance.web")
    assert r.id  # auto-generated
    assert r.type is ResourceType.OTHER
    assert r.provider.value == "aws"
    assert r.tags == {} and r.raw == {}


def test_finding_carries_engine_numbers_and_explanation_source():
    f = Finding(
        resource_id="r1",
        detector="idle_ec2",
        title="Idle EC2 instance",
        severity=Severity.HIGH,
        risk=Risk.LOW,
        current_cost=60.0,
        projected_cost=15.0,
        monthly_savings=45.0,
        evidence={"cpu_pct": 3.2},
        explanation="Downsize; utilization is 3.2%.",
        explanation_source=ExplanationSource.TEMPLATE,
    )
    assert f.monthly_savings == 45.0
    assert f.explanation_source is ExplanationSource.TEMPLATE
    # round-trips through JSON (used by the API layer)
    assert Finding.model_validate(f.model_dump()).monthly_savings == 45.0


def test_analysis_severity_counts():
    a = Analysis(status=AnalysisStatus.COMPLETE)
    findings = [
        Finding(resource_id="r1", detector="d", title="t", severity=Severity.HIGH, risk=Risk.LOW),
        Finding(resource_id="r2", detector="d", title="t", severity=Severity.HIGH, risk=Risk.LOW),
        Finding(resource_id="r3", detector="d", title="t", severity=Severity.LOW, risk=Risk.LOW),
    ]
    assert a.severity_counts(findings) == {"low": 1, "medium": 0, "high": 2}
