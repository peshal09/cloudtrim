"""Prompt-regression golden tests (BLUEPRINT.md §3 Week 2, §6).

Pins the deterministic template outputs (per-finding explanations + the analysis
narrative) to committed golden files. A change to a template or to the evidence
that feeds it fails here, forcing a deliberate review + regeneration rather than a
silent drift. Regenerate with:  UPDATE_GOLDEN=1 pytest packages/ai/tests/test_golden.py

Golden covers only the deterministic path (template + engine), never a live LLM.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from ai import AIConfig, make_explainer, prioritize_analysis
from engine.pipeline import analyze

_GOLDEN = Path(__file__).parent / "golden" / "explanations.json"
_NO_KEY = AIConfig(api_key=None)

# Self-contained dataset covering every detector (stable regardless of the app's
# sample data). Fixed inputs -> fixed template outputs.
_TF = """
resource "aws_instance" "web" {
  instance_type = "t3.xlarge"
  tags = { env = "prod", owner = "team-platform", Name = "web" }
}
resource "aws_instance" "batch" {
  instance_type = "c5.4xlarge"
  tags = { env = "prod", Name = "batch" }
}
resource "aws_db_instance" "main" {
  instance_class = "db.m5.xlarge"
  tags = { env = "prod", owner = "team-data" }
}
resource "aws_s3_bucket" "logs" {
  bucket = "acme-prod-logs"
  tags = { env = "prod", owner = "team-platform" }
}
"""

_CSV = """identifier,service,region,instance_type,monthly_cost,cpu_utilization
aws_instance.web,ec2,us-east-1,t3.xlarge,121.47,4.1
aws_db_instance.main,rds,us-east-1,db.m5.xlarge,249.66,9.0
i-0deadbeef42,ec2,us-east-1,t3.large,60.74,0.0
"""


def _current() -> dict[str, str]:
    result = analyze(
        terraform_source=_TF,
        billing_source=_CSV,
        explain=make_explainer(_NO_KEY),
    )
    out = {f.id: f.explanation or "" for f in result.findings}
    out["_narrative"] = prioritize_analysis(result.aggregate, config=_NO_KEY).text
    return dict(sorted(out.items()))


def test_template_outputs_match_golden():
    current = _current()

    if os.environ.get("UPDATE_GOLDEN"):
        _GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        _GOLDEN.write_text(json.dumps(current, indent=2) + "\n")
        return

    assert _GOLDEN.exists(), "golden missing; run UPDATE_GOLDEN=1 pytest ..."
    golden = json.loads(_GOLDEN.read_text())

    assert set(current) == set(golden), "finding set changed vs golden"
    for key, text in golden.items():
        assert current[key] == text, (
            f"template drift for {key!r}:\n  golden:  {text!r}\n  current: {current[key]!r}\n"
            "If intended, regenerate: UPDATE_GOLDEN=1 pytest packages/ai/tests/test_golden.py"
        )
