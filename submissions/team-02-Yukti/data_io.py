"""Loaders that keep detector inputs and ground truth strictly separate."""
from __future__ import annotations

import pandas as pd

from src import config as C


def load_metrics(path=C.METRICS_FILE) -> pd.DataFrame:
    """Detector input: daily metrics only. Raises if any label column leaks in."""
    df = pd.read_csv(path, parse_dates=["date"])
    extra = set(df.columns) - set(C.METRIC_COLUMNS)
    if extra:
        raise ValueError(f"Unexpected (possibly label) columns in metrics: {extra}")
    return df[C.METRIC_COLUMNS].sort_values(["campaign_id", "date"]).reset_index(drop=True)


def load_labels(path=C.LABELS_FILE) -> pd.DataFrame:
    """Ground truth. For evaluation only - never pass to a detector."""
    return pd.read_csv(path, parse_dates=["start_date", "end_date"])


def load_benign(path=C.BENIGN_FILE) -> pd.DataFrame:
    """Known non-incident shifts. For evaluation/analysis only."""
    return pd.read_csv(path, parse_dates=["start_date"])


def assign_period(dates: pd.Series) -> pd.Series:
    """Map dates to 'dev' (calibration) or 'eval' (held-out).

    Synthetic-benchmark concept only: it depends on C.DEV_END, which is tuned
    to the synthetic benchmark's own date range. Not meaningful for the PS-04
    supplied dataset (see load_ps04_metrics / pipeline.run_ps04_detection),
    which has no calibration/held-out split and no ground-truth labels at all.
    """
    return pd.Series(
        ["dev" if d <= C.DEV_END else "eval" for d in pd.to_datetime(dates)],
        index=dates.index,
    )


def load_ps04_metrics(path=C.PS04_FILE) -> tuple[pd.DataFrame, pd.DataFrame]:
    """PS-04 supplied dataset. Returns (metrics, campaign_metadata), kept apart
    exactly as load_metrics/load_labels keep the synthetic metrics and ground
    truth apart. `metrics` is the only frame ever passed to the detector; it
    has no ground-truth incident labels at all (the organizers supplied none).
    `campaign_metadata` (campaign_name, channel, vertical, landing_page_group)
    is one row per campaign_id, for joining onto records afterwards - never
    for scoring.

    Raises if the file's columns don't match the documented PS-04 schema.
    """
    df = pd.read_csv(path, parse_dates=["date"])
    missing = set(C.PS04_RAW_COLUMNS) - set(df.columns)
    extra = set(df.columns) - set(C.PS04_RAW_COLUMNS)
    if missing or extra:
        raise ValueError(f"PS-04 file does not match expected schema: missing={missing} extra={extra}")

    metrics = (df[C.PS04_METRIC_COLUMNS]
               .sort_values(["campaign_id", "date"]).reset_index(drop=True))
    metadata = (df[C.PS04_METADATA_COLUMNS]
                .drop_duplicates("campaign_id")
                .sort_values("campaign_id").reset_index(drop=True))
    return metrics, metadata
