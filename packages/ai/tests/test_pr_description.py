from ai import AIConfig, describe_pr
from ai.pr_description import render_template
from engine.models import ExplanationSource, Finding, Risk, Severity

NO_KEY = AIConfig(api_key=None)


def _rightsize(ident, cur, tgt, savings, risk=Risk.MEDIUM):
    return Finding(
        id=f"idle_ec2:{ident}",
        resource_id="r",
        detector="idle_ec2",
        title="Idle EC2",
        severity=Severity.HIGH,
        risk=risk,
        monthly_savings=savings,
        evidence={"current_instance_type": cur, "target_instance_type": tgt},
    )


FINDINGS = [
    _rightsize("aws_instance.web", "t3.xlarge", "t3.large", 60.73),
    _rightsize("aws_db_instance.main", "db.m5.xlarge", "db.m5.large", 124.83, Risk.HIGH),
]


def test_template_pr_body_is_grounded():
    pr = describe_pr(FINDINGS, config=NO_KEY)
    assert pr.source is ExplanationSource.TEMPLATE
    assert "$185.56" in pr.title  # 60.73 + 124.83
    assert "$185.56" in pr.body
    assert "t3.xlarge → t3.large" in pr.body
    assert "aws_db_instance.main" in pr.body


def test_template_lists_each_change():
    body = render_template(FINDINGS)
    assert body.count("| `") == 2  # one table row per finding
    assert "$60.73" in body and "$124.83" in body


class _Resp:
    stop_reason = "end_turn"

    def __init__(self, text):
        self.content = [type("B", (), {"type": "text", "text": text})()]


class _Client:
    def __init__(self, text):
        self.messages = type("M", (), {"create": lambda _s, **k: _Resp(text)})()


def test_llm_body_used_when_valid():
    good = "Rightsizes two resources for $185.56/mo total: web saves $60.73/mo."
    pr = describe_pr(FINDINGS, config=AIConfig(api_key="k"), client_factory=lambda c: _Client(good))
    assert pr.source is ExplanationSource.LLM
    assert pr.body == good


def test_llm_hallucination_falls_back():
    bad = "This saves $9,999.00/mo."
    pr = describe_pr(FINDINGS, config=AIConfig(api_key="k"), client_factory=lambda c: _Client(bad))
    assert pr.source is ExplanationSource.TEMPLATE
    assert "$185.56" in pr.body
