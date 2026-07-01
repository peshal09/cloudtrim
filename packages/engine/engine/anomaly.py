"""Cost anomaly detection + forecast (BLUEPRINT.md §10 stretch; Week 6).

Deterministic, offline: takes a historical cost CSV (period, service, cost) and
flags spikes with a robust **modified z-score** (median + MAD — resistant to the very
outliers we're hunting, unlike mean/stdev), attributing each anomaly to the service
that drove it. A simple linear forecast projects next period's spend.
"""

from __future__ import annotations

import csv
import io
import statistics
from pathlib import Path

from pydantic import BaseModel

_ALIASES = {
    "period": ("period", "month", "date", "billing_period"),
    "service": ("service", "type", "resource_type"),
    "cost": ("cost", "amount", "monthly_cost", "unblended_cost"),
}


class Anomaly(BaseModel):
    service: str
    period: str
    expected_cost: float
    actual_cost: float
    deviation_pct: float
    z_score: float
    severity: str  # "high" | "medium"
    note: str


class SeriesPoint(BaseModel):
    period: str
    cost: float


class TrendReport(BaseModel):
    anomalies: list[Anomaly]
    forecast_by_service: dict[str, float]
    forecast_total: float
    series: dict[str, list[SeriesPoint]]  # per-service history, for charting


def parse_cost_history(source: str | Path) -> dict[str, list[tuple[str, float]]]:
    """service -> [(period, cost), ...] in file order."""
    text = Path(source).read_text() if _looks_like_path(source) else str(source)
    history: dict[str, list[tuple[str, float]]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        service = _pick(norm, "service")
        period = _pick(norm, "period")
        cost = _to_float(_pick(norm, "cost"))
        if not service or not period or cost is None:
            continue
        history.setdefault(service, []).append((period, cost))
    return history


def detect_anomalies(
    history: dict[str, list[tuple[str, float]]],
    z_threshold: float = 3.5,
    min_points: int = 4,
) -> list[Anomaly]:
    out: list[Anomaly] = []
    for service, series in history.items():
        costs = [c for _, c in series]
        if len(costs) < min_points:
            continue
        median = statistics.median(costs)
        mad = statistics.median([abs(c - median) for c in costs])
        for period, cost in series:
            if cost <= median:  # only spikes are waste
                continue
            if mad > 0:
                z = 0.6745 * (cost - median) / mad
            else:  # degenerate spread -> fall back to standard z
                std = statistics.pstdev(costs)
                z = (cost - statistics.fmean(costs)) / std if std > 0 else 0.0
            if z < z_threshold:
                continue
            dev = round((cost - median) / median * 100, 1) if median else 0.0
            out.append(
                Anomaly(
                    service=service,
                    period=period,
                    expected_cost=round(median, 2),
                    actual_cost=round(cost, 2),
                    deviation_pct=dev,
                    z_score=round(z, 2),
                    severity="high" if z >= 5 else "medium",
                    note=(
                        f"{service} spend in {period} is {dev:.0f}% above its typical "
                        f"${median:,.2f}"
                    ),
                )
            )
    return sorted(out, key=lambda a: -a.z_score)


def forecast_next(history: dict[str, list[tuple[str, float]]]) -> tuple[dict[str, float], float]:
    """Project next period per service via a linear fit; returns (by_service, total)."""
    by_service: dict[str, float] = {}
    for service, series in history.items():
        ys = [c for _, c in series]
        if len(ys) < 2:
            by_service[service] = round(ys[-1], 2) if ys else 0.0
            continue
        xs = list(range(len(ys)))
        slope, intercept = statistics.linear_regression(xs, ys)
        by_service[service] = round(max(0.0, slope * len(ys) + intercept), 2)
    return by_service, round(sum(by_service.values()), 2)


def analyze_trends(source: str | Path) -> TrendReport:
    history = parse_cost_history(source)
    by_service, total = forecast_next(history)
    series = {
        svc: [SeriesPoint(period=p, cost=c) for p, c in points] for svc, points in history.items()
    }
    return TrendReport(
        anomalies=detect_anomalies(history),
        forecast_by_service=by_service,
        forecast_total=total,
        series=series,
    )


def _pick(row: dict[str, str], field: str) -> str:
    for alias in _ALIASES[field]:
        if row.get(alias):
            return row[alias]
    return ""


def _to_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace("$", "").replace(",", ""))
    except ValueError:
        return None


def _looks_like_path(source: str | Path) -> bool:
    if isinstance(source, Path):
        return True
    return "\n" not in source and len(source) < 4096 and Path(source).exists()
