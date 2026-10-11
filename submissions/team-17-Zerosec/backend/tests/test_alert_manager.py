import pandas as pd

from app.services.alert_manager import (AlertConfig, Finding, build_findings, manage_alerts, route,
                                        summarize)
from app.services.detector import Anomaly, DetectionResult, DetectorConfig, classify_severity
from app.services.diagnosis import Diagnosis

cfg = AlertConfig()
DAY0 = pd.Timestamp("2026-01-01")


def A(campaign, day, metric, score, severity=None, pct=None):
    pct = pct if pct is not None else (0.4 if score > 0 else -0.4)
    return Anomaly(campaign_id=campaign, date=DAY0 + pd.Timedelta(days=day), metric=metric,
                   observed=100 * (1 + pct), expected=100.0, lower=80.0, upper=120.0, score=score,
                   pct_change=pct, direction="up" if score > 0 else "down",
                   severity=severity or classify_severity(score, pct, metric, DetectorConfig()),
                   history_points=28)


def det(anoms, extra_rows=()):
    rows = [{"campaign_id": a.campaign_id, "date": a.date, "metric": a.metric, "observed": a.observed,
             "expected": a.expected, "lower": a.lower, "upper": a.upper, "score": a.score,
             "pct_change": a.pct_change, "history_points": 28, "is_anomaly": True} for a in anoms]
    return DetectionResult(anomalies=list(anoms), scores=pd.DataFrame(rows + list(extra_rows)))


def score_row(campaign, day, metric, score, pct):
    return {"campaign_id": campaign, "date": DAY0 + pd.Timedelta(days=day), "metric": metric,
            "observed": 100 * (1 + pct), "expected": 100.0, "lower": 80.0, "upper": 120.0, "score": score,
            "pct_change": pct, "history_points": 28, "is_anomaly": False}


def F(campaign, day, alert_type="tracking_issue", severity="medium", category="incident"):
    a = A(campaign, day, "conversions", -5.0, severity=severity)
    d = Diagnosis(alert_type, "t", "explanation may vary", ["x"], ["step"])
    return Finding(campaign_id=campaign, date=a.date, primary=a, related=[], severity=severity,
                   diagnosis=d, category=category)


def portfolio_detection(n_campaigns, anomalous):
    anoms = [A(f"C{i}", 30, "clicks", 5.0, pct=0.4) for i in range(anomalous)]
    extra = [score_row(f"C{i}", 30, "clicks", 1.5, 0.4) for i in range(anomalous, n_campaigns)]
    return det(anoms, extra)


def test_related_metrics_same_day_grouped():
    findings, dups = build_findings(det([A("C1", 10, "conversions", -8), A("C1", 10, "revenue", -6),
                                         A("C1", 10, "cvr", -7)]), cfg)
    assert len(findings) == 1 and findings[0].primary.metric == "conversions"
    assert len(findings[0].related) == 2


def test_duplicates_removed():
    _, dups = build_findings(det([A("C1", 10, "spend", 5), A("C1", 10, "spend", 5)]), cfg)
    assert dups == 1


def test_repeats_within_cooldown_suppressed_but_kept():
    fs = [F("C1", d) for d in range(5)]
    [alert] = manage_alerts(fs, cfg)
    assert [f.status for f in fs] == ["new"] + ["suppressed"] * 4
    assert len(alert.notifications) == 1 and alert.suppressed_count == 4 and len(alert.findings) == 5


def test_escalation_not_hidden_by_cooldown():
    fs = [F("C1", 0), F("C1", 1), F("C1", 2, severity="critical")]
    [alert] = manage_alerts(fs, cfg)
    assert [f.status for f in fs] == ["new", "suppressed", "escalated"]
    assert alert.severity == "critical" and alert.routing == "immediate" and len(alert.notifications) == 2


def test_reopen_after_recovery():
    fs = [F("C1", 0), F("C1", 1), F("C1", 10)]
    a1, a2 = manage_alerts(fs, cfg)
    assert fs[2].status == "reopened" and a2.reopened_from == a1.alert_id


def test_different_types_are_separate_alerts():
    assert len(manage_alerts([F("C1", 0), F("C1", 0, alert_type="spend_spike")], cfg)) == 2


def test_portfolio_shift_routed_as_seasonality():
    findings, _ = build_findings(portfolio_detection(n_campaigns=6, anomalous=4), cfg)
    assert len(findings) == 4 and {f.category for f in findings} == {"seasonality"}
    assert all(f.diagnosis.alert_type == "portfolio_shift" and "of 6 campaigns" in f.diagnosis.explanation
               for f in findings)
    assert {a.routing for a in manage_alerts(findings, cfg)} == {"digest"}


def test_small_portfolio_never_called_seasonal():
    findings, _ = build_findings(portfolio_detection(n_campaigns=3, anomalous=3), cfg)
    assert {f.category for f in findings} == {"incident"}


def test_campaign_specific_drop_during_surge_stays_incident():
    d = portfolio_detection(n_campaigns=6, anomalous=6)
    drop = A("C1", 30, "conversions", -12.0, pct=-0.9)
    d = DetectionResult(anomalies=d.anomalies + [drop],
                        scores=pd.concat([d.scores, det([drop]).scores], ignore_index=True))
    findings, _ = build_findings(d, cfg)
    [c1] = [f for f in findings if f.campaign_id == "C1"]
    assert c1.primary.metric == "conversions" and c1.category == "incident"


def test_summary_invariants():
    anoms = [A("C1", 0, "spend", 5), A("C1", 0, "spend", 5), A("C1", 0, "clicks", 4),
             A("C1", 1, "spend", 5), A("C1", 2, "spend", 12), A("C2", 0, "spend", -5), A("C1", 20, "spend", 5)]
    d = det(anoms)
    findings, dups = build_findings(d, cfg)
    alerts = manage_alerts(findings, cfg)
    s = summarize(len(d.anomalies), dups, findings, alerts)
    assert s.anomalies_detected == s.duplicates_removed + s.findings + s.grouped_alerts
    assert s.findings == s.new_alerts + s.reopened_alerts + s.escalated_alerts + s.suppressed_alerts
    assert s.notifications_sent == s.new_alerts + s.reopened_alerts + s.escalated_alerts
    assert s.notifications_sent == s.immediate_notifications + s.digest_notifications
    assert (s.duplicates_removed, s.grouped_alerts, s.escalated_alerts, s.reopened_alerts) == (1, 1, 1, 1)


def test_route():
    assert route("high", "incident") == "immediate" and route("medium", "incident") == "digest"
    assert route("critical", "seasonality") == "digest"


def test_campaign_collapse_on_portfolio_down_day_stays_incident():
    # 6 campaigns dip ~20% (e.g. a weekend); C0 collapses 98% the same day
    extra = [score_row(f"C{i}", 30, "clicks", -1.5, -0.2) for i in range(1, 6)]
    collapse = A("C0", 30, "clicks", -12.0, pct=-0.98)
    findings, _ = build_findings(det([collapse], extra), cfg)
    [f] = findings
    assert f.category == "incident"


def test_dashboard_metric_invariants_and_actionable_population():
    # Build simulated alerts across all severity tiers
    anoms = [
        A("C1", 0, "spend", 10.0, severity="critical"),
        A("C2", 0, "conversions", -5.0, severity="high"),
        A("C3", 0, "cpa", 4.0, severity="medium"),
        A("C4", 0, "clicks", 3.0, severity="low"),
    ]
    findings, _ = build_findings(det(anoms), cfg)
    alerts = manage_alerts(findings, cfg)
    severities = [a.severity for a in alerts]
    
    crit_count = severities.count("critical")
    high_count = severities.count("high")
    med_count = severities.count("medium")
    low_count = severities.count("low")
    
    actionable_count = crit_count + high_count
    digest_count = med_count + low_count
    total_count = len(alerts)
    
    # Invariant: Actionable + Digest equals total alerts, donut slices sum exactly to total
    assert actionable_count + digest_count == total_count
    assert crit_count + high_count + med_count + low_count == total_count
    assert actionable_count == 2
    assert total_count == 4
