"""Alert fatigue management: from raw anomalies to a few meaningful notifications.

1. Group: all anomalies for one campaign-day become one Finding.
2. Seasonality: if most of the portfolio moved the same way that day, the
   finding is a market-wide shift, not a broken campaign, and goes to the digest.
3. Episodes: findings of the same type for the same campaign form one Alert.
   Repeats inside the cooldown are suppressed (kept as evidence, no
   notification), a severity increase escalates, and a return after recovery
   reopens. Nothing is hidden: every finding stays attached to its alert.
"""
from dataclasses import dataclass, field

import pandas as pd

from app.services.detector import SEVERITY_RANK, Anomaly, DetectionResult
from app.services.diagnosis import METRIC_LABELS, Diagnosis, describe_anomaly, diagnose


@dataclass(frozen=True)
class AlertConfig:
    cooldown_days: int = 3              # a gap of MORE than this many days between findings = recovered
    portfolio_share: float = 0.5        # share of campaigns moving together => portfolio shift
    portfolio_min_pct: float = 0.15     # how far each campaign must move to count
    min_portfolio_campaigns: int = 5    # never call it seasonality with fewer scored campaigns
    max_move_vs_portfolio: float = 2.0  # a campaign moving > 2x the typical portfolio move is its own problem


@dataclass
class Finding:
    campaign_id: str
    date: pd.Timestamp
    primary: Anomaly
    related: list[Anomaly]
    severity: str
    diagnosis: Diagnosis
    category: str            # "incident" | "seasonality"
    status: str = ""         # "new" | "reopened" | "escalated" | "suppressed"


@dataclass
class Alert:
    alert_id: str
    campaign_id: str
    alert_type: str
    category: str
    severity: str
    routing: str             # "immediate" | "digest"
    first_date: pd.Timestamp
    last_date: pd.Timestamp
    findings: list[Finding] = field(default_factory=list)
    notifications: list[tuple[pd.Timestamp, str, str]] = field(default_factory=list)  # (date, kind, routing)
    reopened_from: str | None = None

    @property
    def suppressed_count(self) -> int:
        return sum(f.status == "suppressed" for f in self.findings)


@dataclass
class AlertSummary:
    anomalies_detected: int
    duplicates_removed: int
    findings: int
    grouped_alerts: int
    new_alerts: int
    reopened_alerts: int
    escalated_alerts: int
    suppressed_alerts: int
    notifications_sent: int
    immediate_notifications: int
    digest_notifications: int
    alerts_total: int


def route(severity: str, category: str) -> str:
    if category == "incident" and severity in ("high", "critical"):
        return "immediate"
    return "digest"


def find_portfolio_shifts(scores: pd.DataFrame, cfg: AlertConfig) -> dict[tuple, tuple[int, int, float]]:
    """(date, metric, direction) -> (campaigns_moving, campaigns_scored, typical_move) for portfolio-wide moves.

    typical_move is the median pct_change of the campaigns that moved.
    """
    shifts: dict[tuple, tuple[int, int, float]] = {}
    scored = scores[scores["pct_change"].notna()]
    keys = [scored["date"], scored["metric"]]
    pct = scored["pct_change"]
    up, down = pct >= cfg.portfolio_min_pct, pct <= -cfg.portfolio_min_pct
    counts = pd.DataFrame({
        "n": scored.groupby(keys).size(),
        "up": up.groupby(keys).sum(),
        "down": down.groupby(keys).sum(),
        "up_typical": pct.where(up).groupby(keys).median(),
        "down_typical": pct.where(down).groupby(keys).median(),
    })
    counts = counts[counts["n"] >= cfg.min_portfolio_campaigns]
    for (date, metric), row in counts.iterrows():
        for direction in ("up", "down"):
            if row[direction] / row["n"] >= cfg.portfolio_share:
                shifts[(date, metric, direction)] = (int(row[direction]), int(row["n"]),
                                                     float(row[f"{direction}_typical"]))
    return shifts


def _seasonal_diagnosis(primary: Anomaly, moving: int, n: int, typical: float, cfg: AlertConfig) -> Diagnosis:
    label = METRIC_LABELS.get(primary.metric, primary.metric).lower()
    explanation = " ".join([
        describe_anomaly(primary),
        f"{moving} of {n} campaigns saw {label} move more than {cfg.portfolio_min_pct * 100:.0f}% in the same "
        f"direction on this date (typical move {typical * 100:+.0f}%), so this looks like a market-wide or "
        "seasonal shift rather than a fault in this campaign.",
        "This may indicate seasonal demand or a market-wide event.",
        "Suggested first check: Compare with known seasonal events or the same period last year; "
        "no campaign-level fix may be needed.",
    ])
    return Diagnosis("portfolio_shift", "Portfolio-wide shift (likely seasonality)", explanation,
                     ["seasonal demand", "a market-wide event affecting all campaigns"],
                     ["Compare with known seasonal events or the same period last year; no campaign-level fix may be needed.",
                      "Watch for campaigns that move against the portfolio trend: those are worth investigating."])


def build_findings(detection: DetectionResult, cfg: AlertConfig) -> tuple[list[Finding], int]:
    # 1. De-duplicate identical (campaign, date, metric) anomalies.
    unique: dict[tuple, Anomaly] = {}
    for a in detection.anomalies:
        unique.setdefault((a.campaign_id, a.date, a.metric), a)
    duplicates_removed = len(detection.anomalies) - len(unique)

    # 2. Group per campaign-day; the strongest anomaly is the primary one.
    by_day: dict[tuple, list[Anomaly]] = {}
    for a in unique.values():
        by_day.setdefault((a.campaign_id, a.date), []).append(a)

    scores = detection.scores
    day_scores: dict[tuple, dict[str, dict]] = {}
    if len(scores):
        keys = pd.DataFrame(list(by_day), columns=["campaign_id", "date"])
        relevant = scores.merge(keys, on=["campaign_id", "date"])
        for r in relevant.itertuples(index=False):
            if pd.notna(r.score):
                day_scores.setdefault((r.campaign_id, r.date), {})[r.metric] = {
                    "observed": r.observed, "expected": r.expected, "score": r.score}
    shifts = find_portfolio_shifts(scores, cfg) if len(scores) else {}

    findings = []
    for (campaign_id, date), anomalies in sorted(by_day.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        anomalies.sort(key=lambda a: (SEVERITY_RANK[a.severity], abs(a.score)), reverse=True)
        primary = anomalies[0]
        shift = shifts.get((date, primary.metric, primary.direction))
        # Only call it seasonality if this campaign moved roughly like the rest of the portfolio;
        # a 98% collapse on a day when everyone dipped 15% is still this campaign's problem.
        if shift and abs(primary.pct_change) <= cfg.max_move_vs_portfolio * abs(shift[2]):
            diagnosis, category = _seasonal_diagnosis(primary, *shift, cfg), "seasonality"
        else:
            diagnosis, category = diagnose(anomalies, day_scores.get((campaign_id, date), {})), "incident"
        findings.append(Finding(campaign_id=campaign_id, date=date, primary=primary, related=anomalies[1:],
                                severity=primary.severity, diagnosis=diagnosis, category=category))
    return findings, duplicates_removed


def manage_alerts(findings: list[Finding], cfg: AlertConfig) -> list[Alert]:
    alerts: list[Alert] = []
    latest: dict[tuple, Alert] = {}  # (campaign_id, alert_type) -> most recent episode
    for f in sorted(findings, key=lambda f: (f.date, f.campaign_id)):
        key = (f.campaign_id, f.diagnosis.alert_type)
        episode = latest.get(key)
        gap = (f.date - episode.last_date).days if episode else None

        if episode is None or gap > cfg.cooldown_days:
            # Branch 1: nothing open (or it recovered) -> open a new episode and notify.
            f.status = "reopened" if episode else "new"
            routing = route(f.severity, f.category)
            episode = Alert(
                alert_id=f"{f.campaign_id}:{f.diagnosis.alert_type}:{f.date:%Y-%m-%d}",
                campaign_id=f.campaign_id, alert_type=f.diagnosis.alert_type, category=f.category,
                severity=f.severity, routing=routing, first_date=f.date, last_date=f.date,
                reopened_from=latest[key].alert_id if key in latest else None)
            episode.notifications.append((f.date, f.status, routing))
            alerts.append(episode)
            latest[key] = episode
        elif SEVERITY_RANK[f.severity] > SEVERITY_RANK[episode.severity]:
            # Branch 2: inside the cooldown but materially worse -> escalate and notify again.
            f.status = "escalated"
            episode.severity = f.severity
            episode.routing = route(f.severity, episode.category)
            episode.notifications.append((f.date, "escalated", episode.routing))
        else:
            # Branch 3: same problem, not worse -> suppress the notification, keep the evidence.
            f.status = "suppressed"
        episode.findings.append(f)
        episode.last_date = f.date
    return alerts


def summarize(anomalies_detected: int, duplicates_removed: int, findings: list[Finding],
              alerts: list[Alert]) -> AlertSummary:
    status = [f.status for f in findings]
    notes = [n for a in alerts for n in a.notifications]
    return AlertSummary(
        anomalies_detected=anomalies_detected,
        duplicates_removed=duplicates_removed,
        findings=len(findings),
        grouped_alerts=anomalies_detected - duplicates_removed - len(findings),
        new_alerts=status.count("new"),
        reopened_alerts=status.count("reopened"),
        escalated_alerts=status.count("escalated"),
        suppressed_alerts=status.count("suppressed"),
        notifications_sent=len(notes),
        immediate_notifications=sum(n[2] == "immediate" for n in notes),
        digest_notifications=sum(n[2] == "digest" for n in notes),
        alerts_total=len(alerts),
    )
