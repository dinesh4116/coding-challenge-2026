"""Pydantic response models: the stable contract for the React frontend.

Dates are "YYYY-MM-DD" strings. Every float is either a finite number or null
(never NaN/Infinity). `score` fields are robust z-scores: heuristic scores,
not probabilities.
"""
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str


class Summary(BaseModel):
    campaigns_analyzed: int
    records_analyzed: int = Field(description="Valid campaign-day records after cleaning")
    input_rows: int
    date_start: str
    date_end: str
    days_covered: int
    anomalies_detected: int = Field(description="Metric-level anomalies before any grouping or suppression")
    duplicates_removed: int
    findings: int = Field(description="Campaign-days with at least one anomaly")
    grouped_alerts: int = Field(description="Anomalies merged into a finding as related metrics")
    new_alerts: int
    reopened_alerts: int
    escalated_alerts: int
    suppressed_alerts: int = Field(description="Findings kept as evidence but not notified (inside cooldown)")
    notifications_sent: int = Field(description="new + reopened + escalated: what a human would receive")
    immediate_notifications: int
    digest_notifications: int
    alerts_total: int = Field(description="Alert episodes")


class AnomalyOut(BaseModel):
    metric: str
    observed: float | None
    expected: float | None
    lower: float | None
    upper: float | None
    score: float | None = Field(description="Robust z-score: heuristic, not a probability")
    pct_change: float | None
    direction: str
    severity: str
    history_points: int
    method: str


class OccurrenceOut(BaseModel):
    date: str
    status: str = Field(description="new | reopened | escalated | suppressed")
    severity: str
    explanation: str
    primary: AnomalyOut
    related: list[AnomalyOut]


class NotificationOut(BaseModel):
    date: str
    kind: str = Field(description="new | reopened | escalated")
    routing: str = Field(description="immediate | digest")


class AlertOut(BaseModel):
    alert_id: str
    campaign_id: str
    campaign_name: str | None
    alert_type: str
    title: str
    category: str = Field(description="incident | seasonality")
    severity: str = Field(description="medium | high | critical")
    routing: str = Field(description="immediate | digest")
    first_date: str
    last_date: str
    explanation: str
    possible_causes: list[str]
    diagnostic_steps: list[str]
    primary: AnomalyOut
    occurrences: list[OccurrenceOut]
    notifications: list[NotificationOut]
    suppressed_count: int
    reopened_from: str | None
    suppression_eligible: bool


class TimelinePoint(BaseModel):
    date: str
    values: dict[str, float | None]
    expected: dict[str, float | None]
    lower: dict[str, float | None]
    upper: dict[str, float | None]
    anomaly_metrics: list[str]


class CampaignTimeline(BaseModel):
    campaign_id: str
    campaign_name: str | None
    points: list[TimelinePoint]


class EvaluationOut(BaseModel):
    available: bool
    reason: str | None
    precision: float | None
    recall: float | None
    f1_score: float | None
    precision_immediate: float | None
    alerts_evaluated: int
    immediate_alerts_evaluated: int
    true_positive_alerts: int | None
    false_positive_alerts: int | None
    false_positive_alert_ids: list[str]
    incidents_total: int | None
    incidents_detected: int | None
    detected_incidents: list[dict[str, Any]]
    missed_incidents: list[dict[str, Any]]
    non_incident_windows: list[dict[str, Any]]
    matching_rule: str
    notes: list[str]
    naive_baseline: dict[str, Any] | None


class AnalysisResponse(BaseModel):
    summary: Summary
    config: dict[str, Any]
    metrics_analyzed: list[str]
    alerts: list[AlertOut]
    timeline: list[CampaignTimeline]
    warnings: list[str]
    evaluation: EvaluationOut
    score_note: str


class DemoDataResponse(BaseModel):
    synthetic: bool
    notice: str
    columns: list[str]
    total_records: int
    records: list[dict[str, Any]]
