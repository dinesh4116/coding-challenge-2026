import pandas as pd
import pytest

from app.services.alert_manager import Alert, Finding
from app.services.detector import Anomaly
from app.services.diagnosis import Diagnosis
from app.services.evaluation import evaluate, extract_windows, naive_threshold_baseline

DAY0 = pd.Timestamp("2026-01-01")


def make_frame(days=30, labels=(), seasonal=()):
    rows = []
    for cid in ("A", "B"):
        for d in range(days):
            rows.append({"campaign_id": cid, "date": DAY0 + pd.Timedelta(days=d), "spend": 100.0,
                         "conversions": 10.0, "row_present": True, "is_incident": 0, "incident_type": ""})
    f = pd.DataFrame(rows)
    for cid, d0, d1, kind, flag in [*(("A", a, b, "x", 1) for a, b in labels),
                                    *(("A", a, b, "seasonal_shift", 0) for a, b in seasonal)]:
        m = (f.campaign_id == cid) & f.date.between(DAY0 + pd.Timedelta(days=d0), DAY0 + pd.Timedelta(days=d1))
        f.loc[m, ["is_incident", "incident_type"]] = [flag, kind]
    return f


def alert(campaign, day, category="incident"):
    date = DAY0 + pd.Timedelta(days=day)
    a = Anomaly(campaign, date, "spend", 1, 1, 0, 2, 5, 0.5, "up", "high", 28)
    f = Finding(campaign, date, a, [], "high", Diagnosis("spend_spike", "t", "e", [], []), category, "new")
    return Alert(f"{campaign}:spend_spike:{date:%Y-%m-%d}", campaign, "spend_spike", category, "high",
                 "immediate" if category == "incident" else "digest", date, date, [f], [(date, "new", "x")])


labeled_frame = make_frame(labels=[(10, 12)])


def test_no_labels():
    ev = evaluate(make_frame().drop(columns=["is_incident", "incident_type"]), [], has_labels=False)
    assert ev["available"] is False and ev["precision"] is None and "No ground-truth" in ev["reason"]


def test_extract_windows():
    incidents, others = extract_windows(make_frame(days=60, labels=[(10, 12), (20, 20)], seasonal=[(40, 45)]))
    assert [(i.campaign_id, i.start.day, i.end.day) for i in incidents] == [("A", 11, 13), ("A", 21, 21)]
    assert others[0].incident_type == "seasonal_shift"


def test_precision_recall_f1():
    ev = evaluate(labeled_frame, [alert("A", 11), alert("B", 20)], has_labels=True)
    assert ev["precision"] == 0.5 and ev["recall"] == 1.0 and round(ev["f1_score"], 4) == 0.6667
    assert ev["detected_incidents"][0]["days_to_detect"] == 1 and len(ev["false_positive_alert_ids"]) == 1


def test_missed_incident_listed():
    ev = evaluate(labeled_frame, [], has_labels=True)
    assert ev["recall"] == 0.0 and ev["missed_incidents"][0]["campaign_id"] == "A" and ev["precision"] is None


@pytest.mark.parametrize("day,hit", [(14, True), (15, False)])
def test_tolerance(day, hit):
    assert (evaluate(labeled_frame, [alert("A", day)], True)["incidents_detected"] == 1) is hit


def test_seasonality_alerts_excluded_and_reported():
    ev = evaluate(make_frame(days=60, seasonal=[(40, 45)]), [alert("A", 40, category="seasonality")], True)
    assert ev["alerts_evaluated"] == 0 and ev["non_incident_windows"][0]["alerts_seasonality"] == 1


def test_naive_baseline_counts_30pct_moves():
    f = make_frame()
    f.loc[(f.campaign_id == "A") & (f.date.isin([DAY0 + pd.Timedelta(days=10), DAY0 + pd.Timedelta(days=20)])),
          "spend"] = 140.0
    nb = naive_threshold_baseline(f, incidents=[])
    assert nb["alerts_fired"] == 2


def test_suppressed_repeats_do_not_count_as_detection():
    # alert notified on day 0, repeats suppressed through day 7; incident labeled days 5-7
    a = alert("A", 0)
    for d in range(1, 8):
        f = a.findings[0]
        a.findings.append(Finding(f.campaign_id, DAY0 + pd.Timedelta(days=d), f.primary, [], "high",
                                  f.diagnosis, "incident", "suppressed"))
    ev = evaluate(make_frame(labels=[(5, 7)]), [a], True)
    assert ev["incidents_detected"] == 0 and ev["precision"] == 0.0
