import pytest
from ai import AIConfig, explain_finding, make_explainer, render_template, validate_explanation
from ai.cache import cache
from ai.llm import LLMResult
from engine.models import ExplanationSource, Finding, Resource, ResourceType, Risk, Severity

NO_KEY = AIConfig(api_key=None)


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _rightsize_finding():
    return Finding(
        resource_id="r1",
        detector="idle_ec2",
        title="Idle / underutilized EC2 instance",
        severity=Severity.HIGH,
        risk=Risk.MEDIUM,
        current_cost=60.74,
        projected_cost=30.37,
        monthly_savings=30.37,
        evidence={
            "action": "rightsize",
            "cpu_pct": 3.2,
            "threshold_pct": 10.0,
            "current_instance_type": "t3.large",
            "target_instance_type": "t3.medium",
        },
    )


def _res():
    return Resource(
        id="r1", identifier="aws_instance.web", type=ResourceType.EC2, region="us-east-1"
    )


# --- validation --------------------------------------------------------------


def test_validation_accepts_engine_numbers_rejects_hallucinations():
    f = _rightsize_finding()
    assert validate_explanation("Downsizing saves $30.37/mo from $60.74.", f)[0] is True
    ok, offending = validate_explanation("This saves $999.00/mo.", f)
    assert ok is False
    assert 999.0 in offending


# --- template path (no key) --------------------------------------------------


def test_template_path_when_no_key_is_grounded_and_tagged():
    f, r = _rightsize_finding(), _res()
    explain_finding(f, r, config=NO_KEY)
    assert f.explanation_source is ExplanationSource.TEMPLATE
    assert "$30.37" in f.explanation and "t3.medium" in f.explanation
    # the guardrail passes on the template path too
    assert validate_explanation(f.explanation, f)[0] is True


def test_template_reads_like_a_reviewer_not_a_stub():
    f, r = _rightsize_finding(), _res()
    text = render_template(f, r)
    assert "averaging 3.2% CPU" in text
    assert "Rightsizing t3.large → t3.medium" in text
    assert text.rstrip().endswith("risk is medium.")


def test_governance_finding_has_no_dollar_claim():
    f = Finding(
        resource_id="r2",
        detector="governance",
        title="Governance anti-pattern",
        severity=Severity.LOW,
        risk=Risk.LOW,
        evidence={"action": "governance", "issues": ["missing tags: owner"]},
    )
    explain_finding(f, None, config=NO_KEY)
    assert "$" not in f.explanation
    assert validate_explanation(f.explanation, f)[0] is True


# --- CI-critical: works with zero keys ---------------------------------------


def test_make_explainer_runs_template_path_with_no_key():
    explain = make_explainer(NO_KEY)
    f, r = _rightsize_finding(), _res()
    explain(f, r)  # mutates in place, no network
    assert f.explanation
    assert f.explanation_source is ExplanationSource.TEMPLATE


# --- LLM path via injected fake client ---------------------------------------

# A configured (enabled) provider requires base_url + model + key.
KEYED = AIConfig(api_key="k", base_url="http://llm.test/v1", model="test-model")


class _FakeLLM:
    def __init__(self, text):
        self._text = text

    def complete(self, system, user):
        return LLMResult(self._text)


def test_llm_path_used_when_valid():
    f, r = _rightsize_finding(), _res()
    good = "EC2 aws_instance.web idles at 3.2% CPU; downsize to save $30.37/mo. Low risk."
    explain_finding(f, r, config=KEYED, client_factory=lambda cfg: _FakeLLM(good))
    assert f.explanation_source is ExplanationSource.LLM
    assert f.explanation == good


def test_llm_hallucination_falls_back_to_template():
    f, r = _rightsize_finding(), _res()
    bad = "This resource wastes $12345.00 every month."  # not an engine number
    explain_finding(f, r, config=KEYED, client_factory=lambda cfg: _FakeLLM(bad))
    assert f.explanation_source is ExplanationSource.TEMPLATE
    assert "$30.37" in f.explanation


def test_llm_error_falls_back_to_template():
    def boom(cfg):
        raise RuntimeError("network down")

    f, r = _rightsize_finding(), _res()
    explain_finding(f, r, config=KEYED, client_factory=boom)
    assert f.explanation_source is ExplanationSource.TEMPLATE
