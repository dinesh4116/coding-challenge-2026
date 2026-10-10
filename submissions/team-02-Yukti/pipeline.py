"""End-to-end detection: metrics -> scored records -> episodes.

Reads ONLY data/raw/campaign_metrics.csv. Incident and benign labels are not
loaded here; they are reserved for evaluation.

Run:  python -m src.pipeline
"""
from __future__ import annotations

import pandas as pd

from src import config as C
from src.data_io import assign_period, load_metrics, load_ps04_metrics
from src.detection import compute_baselines
from src.detector_config import PS04_BASE_METRICS, RATIO_METRICS, DetectorConfig
from src.episodes import assign_episodes
from src.explain import add_explanations
from src.scoring import score_and_route

RECORD_COLUMNS = [
    "campaign_id", "date", "period", "metric", "observed", "baseline", "pct_change", "z",
    "direction", "status", "n_history", "magnitude_score", "history_score", "quality_score",
    "evidence_score", "is_anomaly", "severity", "route", "episode_id", "notification",
    "explanation", "diagnostic_action",
]


def run_detection(metrics: pd.DataFrame, cfg: DetectorConfig | None = None,
                   allowed_columns: list[str] | None = None):
    """Return (records, episodes). `metrics` must contain metric columns only.

    `allowed_columns` defaults to the synthetic benchmark's C.METRIC_COLUMNS,
    so existing calls and behaviour are unchanged. Callers for other datasets
    (see run_ps04_detection) pass their own metric-only column set; the guard
    itself is never weakened, only parameterised.
    """
    cfg = cfg or DetectorConfig()
    allowed = allowed_columns or C.METRIC_COLUMNS
    extra = set(metrics.columns) - set(allowed)
    if extra:
        raise ValueError(f"Detector received non-metric columns: {extra}")
    base = compute_baselines(metrics, cfg)
    scored = add_explanations(score_and_route(base, cfg))
    scored["period"] = assign_period(scored["date"])
    records, episodes = assign_episodes(scored, cfg)
    return records[RECORD_COLUMNS], episodes


def run_ps04_detection(metrics: pd.DataFrame, metadata: pd.DataFrame,
                        cfg: DetectorConfig | None = None):
    """End-to-end detection for the PS-04 supplied dataset.

    `metrics` and `metadata` must come from data_io.load_ps04_metrics, which
    never reads any ground-truth labels (the organizers supplied none).
    `metrics` is passed to the detector; `metadata` (campaign_name, channel,
    vertical, landing_page_group) is only joined onto the output records
    afterwards, for grouping and dashboard filters, and never scored.

    Returns (records, episodes). `records['period']` is dropped: the dev/eval
    split is a synthetic-benchmark calibration concept tied to C.DEV_END and
    does not apply to this dataset.
    """
    cfg = cfg or DetectorConfig(metrics=PS04_BASE_METRICS + tuple(RATIO_METRICS))
    records, episodes = run_detection(metrics, cfg=cfg, allowed_columns=C.PS04_METRIC_COLUMNS)
    records = records.drop(columns=["period"]).merge(metadata, on="campaign_id", how="left")
    return records, episodes


def run_ps04_pipeline(cfg: DetectorConfig | None = None):
    """Load the PS-04 file and run run_ps04_detection on it."""
    metrics, metadata = load_ps04_metrics()
    return run_ps04_detection(metrics, metadata, cfg)


def main() -> None:
    records, episodes = run_detection(load_metrics())
    C.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records.to_csv(C.OUTPUT_DIR / "detections.csv", index=False)
    episodes.to_csv(C.OUTPUT_DIR / "episodes.csv", index=False)
    print(f"Scored {len(records)} campaign-day-metric records")
    print(records.groupby(["period", "route"]).size().unstack(fill_value=0).to_string())
    notes = records["notification"].value_counts()
    print(f"Episodes: {len(episodes)} | notifications sent: "
          f"{int(notes.get('new', 0) + notes.get('escalation', 0))} "
          f"(new {notes.get('new', 0)}, escalation {notes.get('escalation', 0)}) | "
          f"suppressed: {notes.get('suppressed', 0)}")


if __name__ == "__main__":
    main()
