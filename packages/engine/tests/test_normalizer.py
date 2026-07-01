from pathlib import Path

from engine.models import Resource, ResourceType
from engine.normalizer import normalize
from engine.parsers import parse_billing, parse_terraform

FIXTURES = Path(__file__).parent / "fixtures"


def _by_id(resources):
    return {r.identifier: r for r in resources}


def test_merge_joins_config_and_billing_by_identifier():
    # plan JSON and billing CSV share identifiers -> all three merge.
    config = parse_terraform(FIXTURES / "sample_plan.json")
    billing = parse_billing(FIXTURES / "sample_billing.csv")
    merged = _by_id(normalize(config, billing, analysis_id="a1"))

    assert len(merged) == 3
    web = merged["aws_instance.web"]
    assert web.type is ResourceType.EC2
    assert web.instance_type == "t3.large"  # from config
    assert web.monthly_cost == 60.74  # from billing
    assert web.utilization == 3.2  # from billing
    assert web.region == "us-east-1"
    assert web.analysis_id == "a1"
    assert web.raw["sources"] == ["config", "billing"]


def test_config_only_resource_has_no_cost():
    config = [
        Resource(identifier="aws_instance.a", type=ResourceType.EC2, instance_type="t3.large")
    ]
    merged = normalize(config, [], analysis_id="a1")
    assert len(merged) == 1
    assert merged[0].monthly_cost is None
    assert merged[0].raw["sources"] == ["config"]


def test_billing_only_resource_is_kept_as_orphan():
    billing = [
        Resource(identifier="i-0abc", type=ResourceType.EC2, monthly_cost=30.0, utilization=0.0)
    ]
    merged = normalize([], billing, analysis_id="a1")
    assert len(merged) == 1
    assert merged[0].identifier == "i-0abc"
    assert merged[0].raw["sources"] == ["billing"]  # in bill, not in IaC


def test_secondary_join_by_name_tag_when_identifiers_differ():
    config = [
        Resource(
            identifier="aws_instance.web",
            type=ResourceType.EC2,
            instance_type="t3.large",
            tags={"Name": "web-1"},
        )
    ]
    billing = [
        Resource(
            identifier="i-0abc",
            type=ResourceType.EC2,
            monthly_cost=60.0,
            utilization=4.0,
            tags={"Name": "web-1"},
        )
    ]
    merged = normalize(config, billing, analysis_id="a1")
    assert len(merged) == 1  # joined, not duplicated
    assert merged[0].identifier == "aws_instance.web"
    assert merged[0].monthly_cost == 60.0
    assert merged[0].raw["sources"] == ["config", "billing"]


def test_config_type_wins_unless_other():
    config = [Resource(identifier="x", type=ResourceType.OTHER)]
    billing = [Resource(identifier="x", type=ResourceType.EC2, monthly_cost=5.0)]
    merged = normalize(config, billing)
    assert merged[0].type is ResourceType.EC2  # OTHER yields to billing's type
