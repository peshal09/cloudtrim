from engine.models import Finding, Resource, ResourceType, Risk, Severity
from engine.risk import apply_risk, score_risk


def _finding(action, resource_id="r"):
    return Finding(
        resource_id=resource_id,
        detector="d",
        title="t",
        severity=Severity.MEDIUM,
        evidence={"action": action},
    )


def _res(rtype=ResourceType.EC2, env="prod", rid="r"):
    tags = {"env": env} if env else {}
    return Resource(id=rid, identifier="x", type=rtype, tags=tags)


def test_governance_is_always_low():
    risk, factors = score_risk(_finding("governance"), _res(env="prod"))
    assert risk is Risk.LOW
    assert factors["score"] == 0


def test_rightsize_prod_ec2_is_medium():
    # rightsize +1, stateless +0, prod +2 = 3
    risk, factors = score_risk(_finding("rightsize"), _res(ResourceType.EC2, "prod"))
    assert risk is Risk.MEDIUM
    assert factors["score"] == 3


def test_rightsize_prod_rds_is_high():
    # rightsize +1, stateful +2, prod +2 = 5
    risk, _ = score_risk(_finding("rightsize"), _res(ResourceType.RDS, "prod"))
    assert risk is Risk.HIGH


def test_rightsize_dev_ec2_is_low():
    # rightsize +1, stateless +0, dev +0 = 1
    risk, _ = score_risk(_finding("rightsize"), _res(ResourceType.EC2, "dev"))
    assert risk is Risk.LOW


def test_delete_prod_rds_is_high():
    # delete +2, stateful +2, prod +2 = 6
    risk, _ = score_risk(_finding("delete"), _res(ResourceType.RDS, "prod"))
    assert risk is Risk.HIGH


def test_delete_dev_ec2_is_medium():
    # delete +2, stateless +0, dev +0 = 2
    risk, _ = score_risk(_finding("delete"), _res(ResourceType.EC2, "dev"))
    assert risk is Risk.MEDIUM


def test_unknown_environment_scores_one():
    risk, factors = score_risk(_finding("rightsize"), _res(ResourceType.EC2, env=None))
    assert factors["score"] == 2  # rightsize +1, stateless +0, unknown +1
    assert risk is Risk.MEDIUM


def test_environment_detection_handles_variants():
    for value, expected_high in (("production", True), ("staging", False)):
        # RDS + delete pins the base high; env only nudges. Use rightsize EC2 to isolate env.
        risk, factors = score_risk(_finding("rightsize"), _res(ResourceType.EC2, value))
        assert (factors["score"] >= 3) is expected_high


def test_apply_risk_sets_field_and_records_factors():
    res = _res(ResourceType.RDS, "prod", rid="r1")
    f = _finding("delete", "r1")
    (out,) = apply_risk([f], [res])
    assert out.risk is Risk.HIGH
    assert "risk_factors" in out.evidence
    assert out.evidence["risk_factors"]["score"] == 6
