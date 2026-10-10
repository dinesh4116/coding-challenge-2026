"""Measure the alerting against ground-truth labels, honestly.

An incident is a run of labeled days for one campaign. We report precision
(how many of our incident alerts were real), recall (how many incidents we
caught), the incidents we missed, and how many alerts a naive "±30% day over
day" rule would have fired on the same data, for comparison.
Without a label column we return nulls and say why. We never invent a number.
"""
from dataclasses import dataclass

import pandas as pd

from app.services.alert_manager import Alert

MATCHING_RULE = (
    "An incident is a contiguous run of labeled days for one campaign. An alert is a true positive if it is "
    "an incident-category alert for the same campaign that sent a notification (new, reopened or escalated) dated from the incident's first "
    "day to its last day plus {tol} days. An incident counts as detected if at least one alert matches it. "
    "Precision = true-positive alerts / incident-category alerts. Recall = detected incidents / labeled "
    "incidents. Seasonality-routed alerts are excluded from precision and reported separately."
)
TUNING_NOTE = ("Detector thresholds were chosen while looking at this same dataset, so these numbers are "
               "optimistic. Treat them as a sanity check, not an out-of-sample result.")
NO_LABELS = ("No ground-truth label column (is_incident / is_anomaly / label) found, so precision and recall "
             "are not computed.")


@dataclass
class Incident:
    campaign_id: str
    start: pd.Timestamp
    end: pd.Timestamp
    incident_type: str


def _runs(rows: pd.DataFrame, mask: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp, str]]:
    """Contiguous runs of consecutive True days -> (start, end, incident_type of first day)."""
    runs, start, prev, kind = [], None, None, ""
    for date, flag, itype in zip(rows["date"], mask, rows.get("incident_type", pd.Series("", index=rows.index))):
        if flag and start is not None and (date - prev).days == 1 and itype == kind:
            prev = date
            continue
        if start is not None:
            runs.append((start, prev, kind))
            start = None
        if flag:
            start, prev, kind = date, date, itype
    if start is not None:
        runs.append((start, prev, kind))
    return runs


def extract_windows(frame: pd.DataFrame) -> tuple[list[Incident], list[Incident]]:
    incidents, others = [], []
    has_type = "incident_type" in frame.columns
    for cid, rows in frame.groupby("campaign_id", sort=True):
        rows = rows.sort_values("date")
        for s, e, k in _runs(rows, rows["is_incident"] == 1):
            incidents.append(Incident(str(cid), s, e, k or "incident"))
        if has_type:
            for s, e, k in _runs(rows, (rows["is_incident"] == 0) & (rows["incident_type"] != "")):
                others.append(Incident(str(cid), s, e, k))
    return incidents, others


def _alert_dates(a: Alert) -> list[pd.Timestamp]:
    """Dates a human was actually notified; suppressed repeats don't count as detection."""
    return [date for date, _, _ in a.notifications]


def _window_hit(dates: list[pd.Timestamp], inc: Incident, tolerance_days: int) -> list[pd.Timestamp]:
    end = inc.end + pd.Timedelta(days=tolerance_days)
    return [d for d in dates if inc.start <= d <= end]


def _f1(p: float | None, r: float | None) -> float | None:
    if p is None or r is None or p + r == 0:
        return None
    return 2 * p * r / (p + r)


def _fmt(d: pd.Timestamp) -> str:
    return f"{d:%Y-%m-%d}"


def evaluate(frame: pd.DataFrame, alerts: list[Alert], has_labels: bool, tolerance_days: int = 2) -> dict:
    empty = {"available": False, "reason": NO_LABELS, "precision": None, "recall": None, "f1_score": None,
             "precision_immediate": None, "alerts_evaluated": 0, "immediate_alerts_evaluated": 0,
             "true_positive_alerts": None, "false_positive_alerts": None, "false_positive_alert_ids": [],
             "incidents_total": None, "incidents_detected": None, "detected_incidents": [],
             "missed_incidents": [], "non_incident_windows": [],
             "matching_rule": MATCHING_RULE.format(tol=tolerance_days), "notes": []}
    if not has_labels or "is_incident" not in frame.columns:
        return empty

    incidents, others = extract_windows(frame)
    evaluated = [a for a in alerts if a.category == "incident"]
    true_ids = set()
    detected, missed = [], []
    for inc in incidents:
        hits = []
        for a in evaluated:
            if a.campaign_id == inc.campaign_id:
                dates = _window_hit(_alert_dates(a), inc, tolerance_days)
                if dates:
                    hits.append((min(dates), a.alert_id))
                    true_ids.add(a.alert_id)
        info = {"campaign_id": inc.campaign_id, "incident_type": inc.incident_type,
                "start": _fmt(inc.start), "end": _fmt(inc.end)}
        if hits:
            first = min(h[0] for h in hits)
            detected.append({**info, "first_alert_date": _fmt(first),
                             "days_to_detect": (first - inc.start).days, "alert_ids": [h[1] for h in hits]})
        else:
            missed.append(info)

    tp = sum(a.alert_id in true_ids for a in evaluated)
    immediate = [a for a in evaluated if a.routing == "immediate"]
    precision = tp / len(evaluated) if evaluated else None
    recall = len(detected) / len(incidents) if incidents else None

    windows = []
    for w in others:
        mine = [a for a in alerts if a.campaign_id == w.campaign_id
                and _window_hit(_alert_dates(a), w, 0)]
        windows.append({"incident_type": w.incident_type, "campaign_id": w.campaign_id,
                        "start": _fmt(w.start), "end": _fmt(w.end),
                        "alerts_immediate": sum(a.routing == "immediate" for a in mine),
                        "alerts_digest": sum(a.routing == "digest" for a in mine),
                        "alerts_seasonality": sum(a.category == "seasonality" for a in mine)})

    notes = [TUNING_NOTE]
    if recall is None:
        notes.append("The label column contains no incidents, so recall is undefined.")
    return {**empty, "available": True, "reason": None,
            "precision": precision, "recall": recall, "f1_score": _f1(precision, recall),
            "precision_immediate": (sum(a.alert_id in true_ids for a in immediate) / len(immediate)
                                    if immediate else None),
            "alerts_evaluated": len(evaluated), "immediate_alerts_evaluated": len(immediate),
            "true_positive_alerts": tp, "false_positive_alerts": len(evaluated) - tp,
            "false_positive_alert_ids": [a.alert_id for a in evaluated if a.alert_id not in true_ids],
            "incidents_total": len(incidents), "incidents_detected": len(detected),
            "detected_incidents": detected, "missed_incidents": missed,
            "non_incident_windows": windows, "notes": notes}


def naive_threshold_baseline(frame: pd.DataFrame, incidents: list[Incident], pct: float = 0.30,
                             metrics=("spend", "conversions"), tolerance_days: int = 2) -> dict:
    """The fixed rule from the problem statement: alert when a metric moves >30% vs yesterday."""
    used = [m for m in metrics if m in frame.columns]
    fired = []  # (campaign_id, date)
    for cid, rows in frame.groupby("campaign_id", sort=True):
        rows = rows.sort_values("date")
        hit = pd.Series(False, index=rows.index)
        for m in used:
            prev = rows[m].shift(1)
            change = (rows[m] - prev) / prev.where(prev > 0)
            hit |= change.abs() > pct
        fired += [(str(cid), d) for d in rows.loc[hit, "date"]]

    def matches(cid, d, inc):
        return cid == inc.campaign_id and inc.start <= d <= inc.end + pd.Timedelta(days=tolerance_days)

    tp = sum(any(matches(c, d, i) for i in incidents) for c, d in fired)
    caught = sum(any(matches(c, d, i) for c, d in fired) for i in incidents)
    return {"rule": f"Alert when {' or '.join(used)} changes more than {pct:.0%} versus the previous day",
            "alerts_fired": len(fired),
            "precision": tp / len(fired) if fired and incidents else None,
            "recall": caught / len(incidents) if incidents else None}
