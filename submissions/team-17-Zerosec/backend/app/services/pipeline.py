"""The whole analysis in one place: load -> features -> detect -> alerts -> evaluate.

Both the API and the CLI call these functions, so they always agree.
Each request is analyzed from scratch (no database): same file + same
settings always gives the same result.
"""
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

from app.schemas import (AlertOut, AnalysisResponse, AnomalyOut, CampaignTimeline, EvaluationOut,
                         NotificationOut, OccurrenceOut, Summary, TimelinePoint)
from app.services.alert_manager import (Alert, AlertConfig, Finding, build_findings, manage_alerts,
                                        summarize)
from app.services.data_loader import LoadResult, load_csv_bytes
from app.services.detector import SEVERITY_RANK, Anomaly, DetectorConfig, detect
from app.services.evaluation import evaluate, extract_windows, naive_threshold_baseline
from app.services.features import add_derived_metrics

DEMO_CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_campaigns.csv"
SCORE_NOTE = ("score is a robust z-score: how many robust standard deviations the value sits from the "
              "campaign's own recent median. It is a heuristic score, not a probability.")


@dataclass(frozen=True)
class AnalysisConfig:
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    match_tolerance_days: int = 2


def clean_number(x) -> float | None:
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, 4) if math.isfinite(x) else None


def _day(d: pd.Timestamp) -> str:
    return f"{d:%Y-%m-%d}"


def _anomaly_out(a: Anomaly) -> AnomalyOut:
    return AnomalyOut(metric=a.metric, observed=clean_number(a.observed), expected=clean_number(a.expected),
                      lower=clean_number(a.lower), upper=clean_number(a.upper), score=clean_number(a.score),
                      pct_change=clean_number(a.pct_change), direction=a.direction, severity=a.severity,
                      history_points=a.history_points, method=a.method)


def _occurrence_out(f: Finding) -> OccurrenceOut:
    return OccurrenceOut(date=_day(f.date), status=f.status, severity=f.severity,
                         explanation=f.diagnosis.explanation, primary=_anomaly_out(f.primary),
                         related=[_anomaly_out(a) for a in f.related])


def _alert_out(a: Alert, names: dict[str, str]) -> AlertOut:
    # The headline is the occurrence that triggered the most recent notification.
    last_date, _, _ = a.notifications[-1]
    head = next(f for f in reversed(a.findings) if f.date == last_date and f.status != "suppressed")
    return AlertOut(
        alert_id=a.alert_id, campaign_id=a.campaign_id, campaign_name=names.get(a.campaign_id),
        alert_type=a.alert_type, title=head.diagnosis.title, category=a.category, severity=a.severity,
        routing=a.routing, first_date=_day(a.first_date), last_date=_day(a.last_date),
        explanation=head.diagnosis.explanation, possible_causes=head.diagnosis.possible_causes,
        diagnostic_steps=head.diagnosis.diagnostic_steps, primary=_anomaly_out(head.primary),
        occurrences=[_occurrence_out(f) for f in a.findings],
        notifications=[NotificationOut(date=_day(d), kind=k, routing=r) for d, k, r in a.notifications],
        suppressed_count=a.suppressed_count, reopened_from=a.reopened_from,
        suppression_eligible=a.category == "incident" and a.severity != "critical",
    )


def _timeline(frame: pd.DataFrame, scores: pd.DataFrame, metrics: list[str],
              names: dict[str, str]) -> list[CampaignTimeline]:
    bands: dict[tuple, dict[str, tuple]] = {}  # (campaign_id, date) -> metric -> (expected, lower, upper, flag)
    for r in scores.itertuples(index=False):
        bands.setdefault((r.campaign_id, r.date), {})[r.metric] = (r.expected, r.lower, r.upper, bool(r.is_anomaly))
    out = []
    for cid, rows in frame.groupby("campaign_id", sort=True):
        points = []
        for r in rows.itertuples(index=False):
            day = bands.get((cid, r.date), {})
            none = (None, None, None, False)
            points.append(TimelinePoint(
                date=_day(r.date),
                values={m: clean_number(getattr(r, m)) for m in metrics},
                expected={m: clean_number(day.get(m, none)[0]) for m in metrics},
                lower={m: clean_number(day.get(m, none)[1]) for m in metrics},
                upper={m: clean_number(day.get(m, none)[2]) for m in metrics},
                anomaly_metrics=[m for m in metrics if day.get(m, none)[3]],
            ))
        out.append(CampaignTimeline(campaign_id=str(cid), campaign_name=names.get(str(cid)), points=points))
    return out


def analyze_load_result(load: LoadResult, config: AnalysisConfig) -> AnalysisResponse:
    frame, derived = add_derived_metrics(load.frame, load.metrics)
    metrics = load.metrics + derived
    detection = detect(frame, metrics, config.detector)
    findings, duplicates = build_findings(detection, config.alerts)
    alerts = manage_alerts(findings, config.alerts)
    s = summarize(len(detection.anomalies), duplicates, findings, alerts)

    evaluation = evaluate(load.frame, alerts, load.has_labels, config.match_tolerance_days)
    incidents = extract_windows(load.frame)[0] if evaluation["available"] else []
    evaluation["naive_baseline"] = naive_threshold_baseline(load.frame, incidents,
                                                            tolerance_days=config.match_tolerance_days)
    for k in ("precision", "recall", "f1_score", "precision_immediate"):
        evaluation[k] = clean_number(evaluation[k])
    for k in ("precision", "recall"):
        evaluation["naive_baseline"][k] = clean_number(evaluation["naive_baseline"][k])

    names: dict[str, str] = {}
    if "campaign_name" in frame.columns:
        names = {str(c): str(n) for c, n in frame.groupby("campaign_id")["campaign_name"].first().items() if n}

    warnings = list(load.warnings)
    valid_days = frame[frame["row_present"]].groupby("campaign_id").size()
    for cid, n in valid_days.items():
        if n < config.detector.min_history + 1:
            warnings.append(f"{cid}: only {n} valid day(s); needs {config.detector.min_history} days of "
                            "history before it can be scored.")

    alerts.sort(key=lambda a: (a.routing != "immediate", -SEVERITY_RANK[a.severity], a.first_date))
    start, end = frame["date"].min(), frame["date"].max()
    return AnalysisResponse(
        summary=Summary(campaigns_analyzed=int(frame["campaign_id"].nunique()), records_analyzed=load.valid_rows,
                        input_rows=load.input_rows, date_start=_day(start), date_end=_day(end),
                        days_covered=int((end - start).days) + 1, **asdict(s)),
        config={**asdict(config.detector), **asdict(config.alerts),
                "match_tolerance_days": config.match_tolerance_days},
        metrics_analyzed=metrics,
        alerts=[_alert_out(a, names) for a in alerts],
        timeline=_timeline(frame, detection.scores, metrics, names),
        warnings=warnings,
        evaluation=EvaluationOut(**evaluation),
        score_note=SCORE_NOTE,
    )


def analyze_csv(content: bytes, config: AnalysisConfig, max_rows: int) -> AnalysisResponse:
    """Raises DataValidationError for files that cannot be analyzed."""
    return analyze_load_result(load_csv_bytes(content, max_rows), config)
