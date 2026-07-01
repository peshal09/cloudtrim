# Evaluation

How we measure whether CloudTrim's engine is correct, and the current baseline.

## Why an eval harness

The dollar figures are the product. A regression that silently drops a detector,
misprices a rightsize, or starts flagging healthy resources would erode the one
thing that makes CloudTrim credible. The eval harness turns "is it correct?" into
a number that CI gates on, and it is **fully deterministic** — snapshot pricing
(tier 1, [ADR-0002](adr/0002-pricing-snapshot-query-api.md)) and the template
explainer, no network, no keys — so the numbers are stable run-to-run.

## How it works

Each labeled fixture is a directory under `eval/fixtures/<name>/` with a
`main.tf` and `costs.csv`, plus a ground-truth file at
`eval/ground_truth/<name>.json` listing the expected findings:

```json
{
  "fixture": "demo",
  "expected_findings": [
    {"detector": "idle_ec2", "identifier": "aws_instance.web", "monthly_savings": 60.73}
  ]
}
```

`eval/run_eval.py` runs the deterministic pipeline (parse → normalize → detect →
price) over every fixture and compares detected findings — keyed by
`(detector, resource identifier)` — against ground truth.

Run it with:

```bash
make eval
```

It exits non-zero on any regression (a missing finding, a false positive, or a
savings mismatch), so CI fails on drift.

## Metrics

- **Precision** — of the findings we reported, how many were expected
  (`TP / (TP + FP)`). Guards against false positives. The `clean` fixture is a
  well-configured stack with **zero** expected findings, so any finding there is a
  false positive and drops precision.
- **Recall** — of the findings that should exist, how many we caught
  (`TP / (TP + FN)`). Guards against missed waste.
- **Savings accuracy** — of the correctly-detected findings, how many priced the
  savings within one cent of ground truth.

The harness reports these overall and **per detector**.

## Fixtures

| Fixture | What it exercises |
|---|---|
| `demo` | All six detectors: idle EC2, overprovisioned RDS, oversized EC2, missing S3 lifecycle, governance, orphaned resource. |
| `fleet` | Idle billed instance + oversized config-only instance + S3 without a lifecycle policy. |
| `clean` | A well-configured, fully-tagged, lifecycle'd stack — **no findings expected** (precision guard). |

## Baseline

Current benchmark (3 fixtures, 9 labeled findings):

| Metric | Value |
|---|---|
| Precision | 100% |
| Recall | 100% |
| Savings accuracy | 100% |

Per-detector precision/recall is 100% across all six detectors. This is a small,
hand-labeled benchmark; the goal for later weeks is to grow it toward a broader
corpus so the numbers carry more weight.

## Adding a fixture

1. Create `eval/fixtures/<name>/main.tf` and `costs.csv`.
2. Create `eval/ground_truth/<name>.json` with the expected findings.
3. Run `make eval` and confirm it scores as intended.

## Related

Prompt-regression golden tests (`packages/ai/tests/test_golden.py`) pin the
template explanation + narrative text so LLM-adjacent output can't drift silently
either — regenerate with `UPDATE_GOLDEN=1 pytest`.
