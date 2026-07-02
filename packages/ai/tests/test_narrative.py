from ai import AIConfig
from ai.llm import LLMResult
from ai.narrative import prioritize_analysis, render_template
from engine.aggregate import AnalysisAggregate, Opportunity
from engine.models import ExplanationSource, Severity

NO_KEY = AIConfig(api_key=None)


def _agg(realistic=305.10, gross=305.10):
    return AnalysisAggregate(
        realistic_monthly_savings=realistic,
        gross_monthly_savings=gross,
        savings_by_detector={"oversized_ec2": 248.20, "idle_ec2": 56.90},
        severity_counts={"low": 1, "medium": 1, "high": 1},
        top_opportunities=[
            Opportunity(
                finding_id="oversized_ec2:aws_instance.batch",
                detector="oversized_ec2",
                resource_identifier="aws_instance.batch",
                title="Oversized EC2 declared in Terraform",
                severity=Severity.MEDIUM,
                risk="medium",
                monthly_savings=248.20,
            ),
            Opportunity(
                finding_id="idle_ec2:aws_instance.web",
                detector="idle_ec2",
                resource_identifier="aws_instance.web",
                title="Idle / underutilized EC2 instance",
                severity=Severity.HIGH,
                risk="low",
                monthly_savings=56.90,
            ),
        ],
    )


def test_template_narrative_is_grounded_and_prioritized():
    n = prioritize_analysis(_agg(), config=NO_KEY)
    assert n.source is ExplanationSource.TEMPLATE
    assert "$305.10" in n.text
    assert "aws_instance.batch" in n.text  # top opportunity named first
    assert "$248.20" in n.text
    # top item is ~81% of $305.10 -> mentioned
    assert "81%" in n.text


def test_template_handles_no_savings():
    agg = AnalysisAggregate(
        realistic_monthly_savings=0.0,
        gross_monthly_savings=0.0,
        savings_by_detector={"governance": 0.0},
        severity_counts={"low": 1, "medium": 0, "high": 0},
        top_opportunities=[],
    )
    text = render_template(agg)
    assert "No dollar-saving changes" in text
    assert "$" not in text


KEYED = AIConfig(api_key="k", base_url="http://llm.test/v1", model="test-model")


class _LLM:
    def __init__(self, text):
        self._text = text

    def complete(self, system, user):
        return LLMResult(self._text)


def test_llm_narrative_used_when_valid():
    good = "You can save $305.10/mo. Start with aws_instance.batch to save $248.20/mo."
    n = prioritize_analysis(_agg(), config=KEYED, client_factory=lambda cfg: _LLM(good))
    assert n.source is ExplanationSource.LLM
    assert n.text == good


def test_llm_hallucination_falls_back_to_template():
    bad = "You can save $9999.00/mo this quarter."
    n = prioritize_analysis(_agg(), config=KEYED, client_factory=lambda cfg: _LLM(bad))
    assert n.source is ExplanationSource.TEMPLATE
    assert "$305.10" in n.text
