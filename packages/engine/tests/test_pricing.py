import pytest
from engine.models import Finding, Resource, ResourceType, Severity
from engine.pricing import PricingClient, apply_pricing


@pytest.fixture
def client(tmp_path):
    # snapshot-only + isolated cache -> deterministic, no network.
    return PricingClient(cache_dir=tmp_path, allow_live=False)


# --- client ------------------------------------------------------------------


def test_snapshot_price_is_hourly_times_hours(client):
    assert client.get_price("t3.large", "us-east-1") == 60.74  # 0.0832 * 730
    assert client.get_price("t3.medium", "us-east-1") == 30.37
    assert client.get_price("db.t3.medium", "us-east-1") == 49.64


def test_region_defaults_to_snapshot_default(client):
    assert client.get_price("t3.large", None) == client.get_price("t3.large", "us-east-1")


def test_unknown_type_returns_none_without_live(client):
    assert client.get_price("z9.mega", "us-east-1") is None
    assert client.get_price(None) is None


# --- savings -----------------------------------------------------------------


def _finding(action, resource_id, current=None, target=None):
    return Finding(
        resource_id=resource_id,
        detector="d",
        title="t",
        severity=Severity.MEDIUM,
        evidence={
            "action": action,
            "current_instance_type": current,
            "target_instance_type": target,
        },
    )


def test_rightsize_savings_from_engine(client):
    res = Resource(
        id="r1", identifier="aws_instance.web", type=ResourceType.EC2, region="us-east-1"
    )
    f = _finding("rightsize", "r1", current="t3.large", target="t3.medium")
    (out,) = apply_pricing([f], [res], client=client)
    assert out.current_cost == 60.74
    assert out.projected_cost == 30.37
    assert out.monthly_savings == 30.37


def test_delete_uses_billed_cost_when_type_unpriced(client):
    res = Resource(id="r2", identifier="i-0orphan", type=ResourceType.EC2, monthly_cost=30.0)
    f = _finding("delete", "r2")  # no instance_type to price
    (out,) = apply_pricing([f], [res], client=client)
    assert out.current_cost == 30.0
    assert out.projected_cost == 0.0
    assert out.monthly_savings == 30.0


def test_governance_finding_stays_zero(client):
    res = Resource(id="r3", identifier="aws_instance.web", type=ResourceType.EC2)
    f = _finding("governance", "r3")
    (out,) = apply_pricing([f], [res], client=client)
    assert (out.current_cost, out.projected_cost, out.monthly_savings) == (0.0, 0.0, 0.0)
