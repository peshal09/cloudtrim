from pathlib import Path

from engine.models import ResourceType
from engine.parsers import parse_billing, parse_terraform

FIXTURES = Path(__file__).parent / "fixtures"


def _by_id(resources):
    return {r.identifier: r for r in resources}


# --- Terraform: HCL fallback -------------------------------------------------


def test_parse_terraform_hcl():
    resources = parse_terraform(FIXTURES / "sample.tf")
    by_id = _by_id(resources)
    assert set(by_id) == {"aws_instance.web", "aws_db_instance.main", "aws_s3_bucket.logs"}

    web = by_id["aws_instance.web"]
    assert web.type is ResourceType.EC2
    assert web.instance_type == "t3.large"  # quotes stripped
    assert web.region == "us-east-1"
    assert web.tags == {"env": "prod", "Name": "web"}
    assert web.monthly_cost is None  # config side has no cost yet

    assert by_id["aws_db_instance.main"].type is ResourceType.RDS
    assert by_id["aws_db_instance.main"].instance_type == "db.t3.medium"
    assert by_id["aws_s3_bucket.logs"].type is ResourceType.S3


def test_parse_terraform_accepts_raw_string():
    text = 'resource "aws_instance" "x" {\n  instance_type = "m5.xlarge"\n}\n'
    resources = parse_terraform(text)
    assert len(resources) == 1
    assert resources[0].instance_type == "m5.xlarge"


# --- Terraform: plan/state JSON ---------------------------------------------


def test_parse_terraform_plan_json_walks_child_modules():
    resources = parse_terraform(FIXTURES / "sample_plan.json")
    by_id = _by_id(resources)
    assert "module.storage.aws_s3_bucket.logs" in by_id  # nested module resolved
    web = by_id["aws_instance.web"]
    assert web.type is ResourceType.EC2
    assert web.instance_type == "t3.large"
    assert web.region == "us-east-1"
    assert web.tags["Name"] == "web"


# --- Billing CSV -------------------------------------------------------------


def test_parse_billing_aliases_and_coercion():
    resources = parse_billing(FIXTURES / "sample_billing.csv")
    by_id = _by_id(resources)

    web = by_id["aws_instance.web"]
    assert web.type is ResourceType.EC2  # "service" alias + keyword map
    assert web.monthly_cost == 60.74  # "$" stripped
    assert web.utilization == 3.2
    assert web.tags == {"env": "prod"}

    db = by_id["aws_db_instance.main"]
    assert db.utilization == 8.0  # "%" stripped

    s3 = by_id["module.storage.aws_s3_bucket.logs"]
    assert s3.type is ResourceType.S3
    assert s3.monthly_cost == 12.50
    assert s3.instance_type is None
    assert s3.utilization is None  # empty cell -> None


def test_parse_billing_skips_rows_without_identifier():
    csv_text = "identifier,cost\n,10.0\naws_instance.y,5.0\n"
    resources = parse_billing(csv_text)
    assert [r.identifier for r in resources] == ["aws_instance.y"]
