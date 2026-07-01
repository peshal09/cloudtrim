from engine.anomaly import analyze_trends, detect_anomalies, forecast_next, parse_cost_history

SPIKE = """period,service,cost
2026-01,s3,150
2026-02,s3,160
2026-03,s3,155
2026-04,s3,158
2026-05,s3,152
2026-06,s3,890
2026-01,ec2,1200
2026-02,ec2,1210
2026-03,ec2,1190
2026-04,ec2,1205
2026-05,ec2,1215
2026-06,ec2,1220
"""


def test_detects_spike_and_attributes_service():
    history = parse_cost_history(SPIKE)
    anomalies = detect_anomalies(history)
    assert len(anomalies) == 1
    a = anomalies[0]
    assert a.service == "s3" and a.period == "2026-06"
    assert a.actual_cost == 890.0
    assert a.expected_cost < 200  # median of the steady months
    assert a.severity == "high"
    assert "above its typical" in a.note


def test_steady_series_has_no_anomalies():
    steady = "period,service,cost\n" + "\n".join(f"2026-0{m},rds,{800 + m}" for m in range(1, 7))
    assert detect_anomalies(parse_cost_history(steady)) == []


def test_short_history_is_skipped():
    two = "period,service,cost\n2026-01,s3,10\n2026-02,s3,9999\n"
    assert detect_anomalies(parse_cost_history(two)) == []  # < min_points


def test_forecast_projects_next_period():
    history = parse_cost_history(
        "period,service,cost\n2026-01,ec2,100\n2026-02,ec2,110\n2026-03,ec2,120\n"
    )
    by_service, total = forecast_next(history)
    assert by_service["ec2"] == 130.0  # linear +10/period
    assert total == 130.0


def test_analyze_trends_bundles_report():
    report = analyze_trends(SPIKE)
    assert len(report.anomalies) == 1
    assert set(report.forecast_by_service) == {"s3", "ec2"}
    assert report.forecast_total > 0
