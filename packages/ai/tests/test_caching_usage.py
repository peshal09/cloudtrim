from ai import AIConfig, explain_finding, usage
from ai.cache import ExplanationCache, cache
from engine.models import ExplanationSource, Finding, Resource, ResourceType, Risk, Severity


def _finding():
    return Finding(
        resource_id="r1",
        detector="idle_ec2",
        title="Idle EC2",
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


# --- cache TTL ---------------------------------------------------------------


def test_cache_entry_expires_after_ttl():
    clock = [1000.0]
    c = ExplanationCache(ttl=10, clock=lambda: clock[0])
    c.set("k", ("text", "template"))
    assert c.get("k") == ("text", "template")
    clock[0] += 11  # past the TTL
    assert c.get("k") is None


def test_cache_no_expiry_when_ttl_zero():
    clock = [0.0]
    c = ExplanationCache(ttl=0, clock=lambda: clock[0])
    c.set("k", ("text", "template"))
    clock[0] += 10_000
    assert c.get("k") == ("text", "template")


# --- fake LLM client with usage -------------------------------------------


class _Usage:
    input_tokens = 120
    output_tokens = 45


class _Resp:
    stop_reason = "end_turn"
    usage = _Usage()

    def __init__(self, text):
        self.content = [type("B", (), {"type": "text", "text": text})()]


class _Client:
    def __init__(self, text):
        self.messages = type("M", (), {"create": lambda _s, **k: _Resp(text)})()


def test_token_usage_is_accounted_on_llm_call():
    cache.clear()
    usage.reset()
    f = _finding()
    good = "EC2 idles at 3.2% CPU; downsize saves $30.37/mo. Low risk."
    explain_finding(f, None, config=AIConfig(api_key="k"), client_factory=lambda c: _Client(good))
    assert f.explanation_source is ExplanationSource.LLM
    assert usage.calls == 1
    assert usage.input_tokens == 120 and usage.output_tokens == 45
    assert usage.estimated_cost_usd > 0
    usage.reset()


# --- prompt-size guardrail ---------------------------------------------------


def test_oversized_prompt_skips_llm_and_uses_template():
    cache.clear()
    f = _finding()
    # a tiny cap forces the guardrail; even a valid LLM reply is skipped
    cfg = AIConfig(api_key="k", max_prompt_chars=10)
    r = Resource(id="r1", identifier="aws_instance.web", type=ResourceType.EC2)
    explain_finding(f, r, config=cfg, client_factory=lambda c: _Client("valid $30.37"))
    assert f.explanation_source is ExplanationSource.TEMPLATE
