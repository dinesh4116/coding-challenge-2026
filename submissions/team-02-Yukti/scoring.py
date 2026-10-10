"""Evidence-strength score, severity and confidence-aware routing.

evidence = magnitude x history_sufficiency x data_quality, each in [0, 1].
This is a transparent HEURISTIC for ordering and routing cases. It is not a
calibrated probability that an incident is real.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.detector_config import DetectorConfig

ALERT, REVIEW, NO_ALERT = "Alert", "Human Review", "No Alert"
SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}


def severity_from_z(abs_z: np.ndarray, cfg: DetectorConfig) -> np.ndarray:
    lo, hi = cfg.severity_bands
    return np.select([abs_z >= hi, abs_z >= lo, abs_z >= cfg.z_threshold],
                     ["high", "medium", "low"], default="none")


def data_quality(df: pd.DataFrame, cfg: DetectorConfig) -> np.ndarray:
    """Completeness of history x denominator adequacy x same-day consistency."""
    q = df["completeness"].fillna(0.0).to_numpy(dtype=float).copy()
    for metric, min_den in cfg.min_denominator.items():
        den = df["_impressions"] if metric == "ctr" else df["_clicks"]
        sel = (df["metric"] == metric).to_numpy()
        q[sel] *= np.clip(den[sel].fillna(0).to_numpy() / min_den, 0, 1)
    inconsistent = ((df["_clicks"] > df["_impressions"])
                    | (df["_conversions"] > df["_clicks"])).to_numpy()
    q[inconsistent] *= 0.5
    return np.clip(q, 0, 1)


def score_and_route(base: pd.DataFrame, cfg: DetectorConfig | None = None) -> pd.DataFrame:
    cfg = cfg or DetectorConfig()
    df = base.copy()
    abs_z = df["z"].abs().to_numpy()
    has_z = ~np.isnan(abs_z)

    df["status"] = np.select(
        [df["observed"].isna(), df["n_history"] < cfg.min_history],
        ["missing_value", "insufficient_history"], default="scored")
    df["pct_change"] = np.where(df["baseline"] > 0,
                                (df["observed"] - df["baseline"]) / df["baseline"].where(df["baseline"] > 0),
                                np.nan)
    df["direction"] = np.where(df["z"] > 0, "up", np.where(df["z"] < 0, "down", "flat"))

    df["magnitude_score"] = np.where(has_z, np.clip(abs_z / cfg.z_full, 0, 1), 0.0)
    df["history_score"] = np.clip(df["n_history"].fillna(0) / cfg.window, 0, 1)
    df["quality_score"] = data_quality(df, cfg)
    df["evidence_score"] = (df["magnitude_score"] * df["history_score"] * df["quality_score"]).round(4)

    anomalous = has_z & (np.nan_to_num(abs_z) >= cfg.z_threshold)
    df["is_anomaly"] = anomalous
    df["severity"] = np.where(anomalous, severity_from_z(np.nan_to_num(abs_z), cfg), "none")
    df["route"] = np.select(
        [anomalous & (df["evidence_score"] >= cfg.alert_evidence), anomalous],
        [ALERT, REVIEW], default=NO_ALERT)
    return df
