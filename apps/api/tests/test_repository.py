import pytest
from api.db.repository import SqlAnalysisRepository
from api.db.session import make_engine
from api.sample_data import SAMPLE_CSV, SAMPLE_K8S, SAMPLE_TF
from engine.pipeline import analyze


@pytest.fixture
def repo():
    # SQLite tier — deterministic, offline (real Postgres is the live tier).
    return SqlAnalysisRepository(make_engine("sqlite://"))


def _sample_result():
    return analyze(
        terraform_source=SAMPLE_TF,
        billing_source=SAMPLE_CSV,
        kubernetes_source=SAMPLE_K8S,
    )


def test_save_and_get_roundtrip(repo):
    result = _sample_result()
    repo.save(result)

    got = repo.get(result.analysis.id)
    assert got is not None
    assert got.analysis.total_monthly_savings == result.analysis.total_monthly_savings
    assert len(got.findings) == len(result.findings)
    assert got.aggregate.realistic_monthly_savings == result.aggregate.realistic_monthly_savings
    # domain types rehydrate (enums, not raw strings)
    assert got.findings[0].severity == result.findings[0].severity


def test_get_missing_returns_none(repo):
    assert repo.get("nope") is None
    assert repo.get_finding("nope") is None


def test_get_finding_with_resource(repo):
    result = _sample_result()
    repo.save(result)
    pair = repo.get_finding("idle_ec2:aws_instance.web")
    assert pair is not None
    finding, resource = pair
    assert finding.detector == "idle_ec2"
    assert resource is not None
    assert resource.identifier == "aws_instance.web"


def test_save_is_idempotent(repo):
    result = _sample_result()
    repo.save(result)
    repo.save(result)  # re-save same id -> replaces, not duplicates
    got = repo.get(result.analysis.id)
    assert len(got.findings) == len(result.findings)


def test_trend_lists_analyses(repo):
    repo.save(_sample_result())
    trend = repo.trend()
    assert len(trend) == 1
    assert trend[0]["total_monthly_savings"] == 494.50
