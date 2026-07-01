"""Eval harness (MVP).

Runs the deterministic engine over labeled fixtures and reports detector
precision/recall + savings accuracy against ground truth. Deterministic by
construction: snapshot pricing (tier 1) + the template explainer, no network.
Week 2 extends this to a benchmark of fixtures with CI gating (BLUEPRINT §3).
"""

from __future__ import annotations

import json
from collections import defaultdict
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

    return tp, fp, fn, savings_ok


def _rate(num: int, den: int) -> float:
    return num / den if den else 1.0


def main() -> int:
    fixtures = [p.stem for p in sorted(_GROUND_TRUTH.glob("*.json"))]
    # per-detector tallies: detector -> [tp, fp, fn]
    tally: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    tp = fp = fn = savings_ok = savings_total = 0

    for name in fixtures:
        tp_keys, fp_keys, fn_keys, ok = _score(name)
        savings_ok += ok
        savings_total += len(tp_keys)
        for det, _ in tp_keys:
            tally[det][0] += 1
        for det, _ in fp_keys:
            tally[det][1] += 1
        for det, _ in fn_keys:
            tally[det][2] += 1
        tp, fp, fn = tp + len(tp_keys), fp + len(fp_keys), fn + len(fn_keys)

    print("\n=== per-detector ===")
    print(f"  {'detector':22} {'TP':>3} {'FP':>3} {'FN':>3}  {'prec':>6} {'recall':>6}")
    for det in sorted(tally):
        t, f, n = tally[det]
        print(f"  {det:22} {t:>3} {f:>3} {n:>3}  {_rate(t, t + f):>6.0%} {_rate(t, t + n):>6.0%}")

    precision = _rate(tp, tp + fp)
    recall = _rate(tp, tp + fn)
    savings_acc = _rate(savings_ok, savings_total)

    print("\n=== summary ===")
    print(f"  fixtures: {len(fixtures)}   findings evaluated: {tp + fn}")
    print(f"  precision: {precision:.2%}   recall: {recall:.2%}")
    print(f"  savings accuracy (matched findings): {savings_acc:.2%}")
    # Non-zero exit if we regressed below a perfect labeled benchmark.
    return 0 if (fp == 0 and fn == 0 and savings_ok == tp) else 1


if __name__ == "__main__":
    raise SystemExit(main())
