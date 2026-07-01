"""Eval harness (MVP).

Runs the deterministic engine over labeled fixtures and reports detector
precision/recall + savings accuracy against ground truth. Deterministic by
construction: snapshot pricing (tier 1) + the template explainer, no network.
Week 2 extends this to a benchmark of fixtures with CI gating (BLUEPRINT §3).
"""

from __future__ import annotations

import json
from pathlib import Path

from engine.detectors import run_detectors
from engine.normalizer import normalize
from engine.parsers import parse_billing, parse_terraform
from engine.pricing import apply_pricing

_ROOT = Path(__file__).parent
_FIXTURES = _ROOT / "fixtures"
_GROUND_TRUTH = _ROOT / "ground_truth"


def _run_fixture(name: str) -> list:
    tf = parse_terraform(_FIXTURES / name / "main.tf")
    billing = parse_billing(_FIXTURES / name / "costs.csv")
    resources = normalize(tf, billing, analysis_id=name)
    return apply_pricing(run_detectors(resources), resources)


def _score(name: str) -> tuple[int, int, int, float, float]:
    truth = json.loads((_GROUND_TRUTH / f"{name}.json").read_text())["expected_findings"]
    expected = {(f["detector"], f["identifier"]): f for f in truth}

    findings = _run_fixture(name)
    # A finding's resource_id is its detector:identifier id, minus the detector prefix.
    detected = {(f.detector, f.id.split(":", 1)[1]): f for f in findings}

    tp = sorted(expected.keys() & detected.keys())
    fp = sorted(detected.keys() - expected.keys())
    fn = sorted(expected.keys() - detected.keys())

    savings_ok = sum(
        1
        for key in tp
        if abs(detected[key].monthly_savings - expected[key]["monthly_savings"]) <= 0.01
    )
    total = round(sum(f.monthly_savings for f in findings), 2)

    print(f"\n=== fixture: {name} ===")
    print(f"  detected {len(detected)} findings, total savings ${total}/mo")
    for key in tp:
        got = detected[key].monthly_savings
        want = expected[key]["monthly_savings"]
        mark = "OK " if abs(got - want) <= 0.01 else "!! "
        print(f"  {mark}{key[0]:20} {key[1]:28} ${got:>7.2f} (want ${want:.2f})")
    for key in fn:
        print(f"  MISS {key[0]:20} {key[1]}")
    for key in fp:
        print(f"  EXTRA {key[0]:20} {key[1]}")

    return len(tp), len(fp), len(fn), savings_ok, len(tp)


def main() -> int:
    fixtures = [p.stem for p in sorted(_GROUND_TRUTH.glob("*.json"))]
    tp = fp = fn = savings_ok = savings_total = 0
    for name in fixtures:
        a, b, c, ok, tot = _score(name)
        tp, fp, fn, savings_ok, savings_total = (
            tp + a,
            fp + b,
            fn + c,
            savings_ok + ok,
            savings_total + tot,
        )

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    savings_acc = savings_ok / savings_total if savings_total else 0.0

    print("\n=== summary ===")
    print(f"  precision: {precision:.2%}   recall: {recall:.2%}")
    print(f"  savings accuracy (matched findings): {savings_acc:.2%}")
    # Non-zero exit if we regressed below a perfect labeled fixture.
    return 0 if (fp == 0 and fn == 0 and savings_ok == tp) else 1


if __name__ == "__main__":
    raise SystemExit(main())
