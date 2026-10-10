"""Campaign-specific rolling robust baselines (median + MAD).

For day t, every quantity is computed from observations strictly before t
(days t-window .. t-1), so later data can never change an earlier score.
Input is the metrics table only; labels are never read here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.detector_config import LOG_METRICS, RATIO_METRICS, DetectorConfig

MAD_TO_SIGMA = 1.4826


def prepare_series(metrics: pd.DataFrame) -> pd.DataFrame:
    """Reindex each campaign to a complete daily calendar (gaps -> NaN) and add ratios."""
    frames = []
    for cid, g in metrics.groupby("campaign_id", sort=True):
        g = g.set_index("date").sort_index()
        full = pd.date_range(g.index.min(), g.index.max(), freq="D")
        g = g.reindex(full).rename_axis("date").reset_index()
        g["campaign_id"] = cid
        frames.append(g)
    df = pd.concat(frames, ignore_index=True)
    for name, (num, den) in RATIO_METRICS.items():
        den_v = df[den].astype(float)
        df[name] = np.where(den_v > 0, df[num] / den_v.where(den_v > 0), np.nan)
    return df


def _transform(metric: str, x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if metric in LOG_METRICS:
        return np.log1p(np.where(x < 0, np.nan, x))
    return x


def _inverse(metric: str, y: float) -> float:
    return float(np.expm1(y)) if metric in LOG_METRICS else float(y)


def _weekday_offsets(y: np.ndarray, dow: np.ndarray, cfg: DetectorConfig) -> np.ndarray:
    """Additive offset per day-of-week (transformed scale), from past data only.

    With weekday_groups="weekend", Sat-Sun share one offset and Mon-Fri another;
    pooling gives more observations per group and a more stable estimate.
    """
    off = np.zeros(7)
    ok = ~np.isnan(y)
    if not cfg.weekday_adjust or ok.sum() < cfg.weekday_min_obs * 2:
        return off
    overall = np.median(y[ok])
    groups = ([[0, 1, 2, 3, 4], [5, 6]] if cfg.weekday_groups == "weekend"
              else [[d] for d in range(7)])
    for days in groups:
        sel = ok & np.isin(dow, days)
        if sel.sum() >= cfg.weekday_min_obs:
            off[days] = np.median(y[sel]) - overall
    return off


def score_series(values, dates, metric: str, cfg: DetectorConfig) -> pd.DataFrame:
    """Score one campaign/metric series. Row t depends only on rows < t."""
    y = _transform(metric, values)
    dow = pd.DatetimeIndex(dates).dayofweek.to_numpy()
    n = len(y)
    out = {k: np.full(n, np.nan) for k in ("baseline", "z", "n_history", "completeness")}
    for t in range(n):
        lo = max(0, t - cfg.window)
        hist, hist_dow = y[lo:t], dow[lo:t]
        valid = ~np.isnan(hist)
        n_valid = int(valid.sum())
        out["n_history"][t] = n_valid
        out["completeness"][t] = n_valid / len(hist) if len(hist) else 0.0
        if n_valid < cfg.min_history:
            continue
        wlo = max(0, t - cfg.weekday_lookback)
        off = _weekday_offsets(y[wlo:t], dow[wlo:t], cfg)
        adj = hist[valid] - off[hist_dow[valid]]
        med = float(np.median(adj))
        mad = float(np.median(np.abs(adj - med)))
        floor = cfg.scale_floor_log if metric in LOG_METRICS else cfg.scale_floor_ratio * abs(med)
        scale = max(MAD_TO_SIGMA * mad, floor, cfg.abs_scale_floor)
        expected = med + off[dow[t]]
        out["baseline"][t] = _inverse(metric, expected)
        if not np.isnan(y[t]):
            out["z"][t] = (y[t] - expected) / scale
    return pd.DataFrame(out)


def compute_baselines(metrics: pd.DataFrame, cfg: DetectorConfig | None = None) -> pd.DataFrame:
    """Long table: one row per campaign x date x metric with observed, baseline, z."""
    cfg = cfg or DetectorConfig()
    wide = prepare_series(metrics)
    rows = []
    for cid, g in wide.groupby("campaign_id", sort=True):
        for metric in cfg.metrics:
            s = score_series(g[metric].to_numpy(), g["date"], metric, cfg)
            s.insert(0, "observed", g[metric].to_numpy(dtype=float))
            s.insert(0, "metric", metric)
            s.insert(0, "date", g["date"].to_numpy())
            s.insert(0, "campaign_id", cid)
            # Same-day context for data-quality checks (not future data).
            for col in ("impressions", "clicks", "conversions"):
                s[f"_{col}"] = g[col].to_numpy(dtype=float)
            rows.append(s)
    return pd.concat(rows, ignore_index=True)
