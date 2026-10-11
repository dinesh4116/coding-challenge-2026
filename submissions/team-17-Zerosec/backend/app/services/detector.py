"""Per-campaign anomaly detector: rolling median / MAD bands, past data only.

For each campaign and metric, a day is compared with the median of the
previous `window_days` days of THAT campaign. The band's width comes from that
campaign's own volatility (MAD), with a small-sample (Student-t) correction
because that volatility is itself estimated from only a few weeks. Count metrics (impressions, clicks,
conversions) use an exact Poisson tail instead, widened by the campaign's own
overdispersion, so a 2-conversions/day campaign is not paged when one
conversion moves but a 2,000/day campaign is when it drifts 10%.
The score is a z-score-like number: a heuristic, not a probability.
"""
import math
import warnings
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

VOLUME_METRICS = ("impressions", "clicks", "spend", "conversions", "revenue")
COUNT_METRICS = ("impressions", "clicks", "conversions")
SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
MAD_TO_SIGMA = 1.4826  # makes MAD comparable to a standard deviation for normal data
MAD_EFFICIENCY = 0.37      # MAD uses ~37% of the information a std-dev would (normal data)
MAJOR_VOLUME_CHANGE = 0.5  # a volume metric dropping >= 50% is at least "high"
_NORMAL = NormalDist()


@dataclass(frozen=True)
class DetectorConfig:
    window_days: int = 28        # how many past days form the baseline
    min_history: int = 14        # minimum valid past days before a day is scored
    z_threshold: float = 3.5     # "sensitivity": |score| needed to flag
    high_z: float = 6.0
    critical_z: float = 10.0
    rel_floor: float = 0.02      # band is never narrower than 2% of the baseline
    min_pct_change: float = 0.05  # ignore statistically odd but tiny (<5%) moves


@dataclass(frozen=True)
class Anomaly:
    campaign_id: str
    date: pd.Timestamp
    metric: str
    observed: float
    expected: float
    lower: float
    upper: float
    score: float
    pct_change: float
    direction: str
    severity: str
    history_points: int
    method: str = "rolling_median_mad"


@dataclass
class DetectionResult:
    anomalies: list[Anomaly]
    scores: pd.DataFrame


def rolling_baseline(history: np.ndarray, window: int, min_history: int) -> tuple[np.ndarray, ...]:
    """For each day: median, MAD and count of the previous `window` valid values.

    Builds a (days x window) matrix where row i holds the `window` values before
    day i (missing days are NaN and simply don't count), then takes medians row-wise.
    Days with fewer than `min_history` valid past values get NaN.
    """
    padded = np.concatenate([np.full(window - 1, np.nan), history])
    rows = np.lib.stride_tricks.sliding_window_view(padded, window)
    count = np.sum(~np.isnan(rows), axis=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN rows -> NaN, which we want
        median = np.nanmedian(rows, axis=1)
        mad = np.nanmedian(np.abs(rows - median[:, None]), axis=1)
    enough = count >= min_history
    return np.where(enough, median, np.nan), np.where(enough, mad, np.nan), count


def poisson_z(observed: float, lam: float) -> float:
    """How surprising is this count if events arrive randomly at rate `lam`?

    Returns the exact Poisson tail probability expressed as an equivalent
    z-score (e.g. 18 expected, 2 observed -> about -4.5). For large counts the
    normal approximation is accurate, so we use it.
    """
    k = int(round(observed))
    if lam > 200 or k > lam + 40 * math.sqrt(lam) + 100:  # large counts, or absurdly far in the tail
        return (k - lam) / math.sqrt(lam)
    top = int(lam + 20 * math.sqrt(lam) + 50) + max(k, 0)
    ks = np.arange(top + 1)
    log_fact = np.concatenate([[0.0], np.cumsum(np.log(np.arange(1, top + 1)))])
    pmf = np.exp(ks * math.log(lam) - lam - log_fact)
    if k < lam:
        p = float(pmf[: k + 1].sum())
        return min(_NORMAL.inv_cdf(min(max(p, 1e-300), 0.5)), 0.0)
    if k > lam:
        p = float(pmf[k:].sum())
        return max(-_NORMAL.inv_cdf(min(max(p, 1e-300), 0.5)), 0.0)
    return 0.0


def t_to_z(t: np.ndarray, dof: np.ndarray) -> np.ndarray:
    """Convert a t-statistic to the equally-surprising z-score (Wallace's approximation).

    The band width comes from only ~28 noisy days, so it is itself uncertain;
    a deviation of t "estimated sigmas" is less surprising than t true sigmas.
    """
    dof = np.maximum(dof, 1.0)
    return np.sign(t) * (8 * dof + 1) / (8 * dof + 3) * np.sqrt(dof * np.log1p(t ** 2 / dof))


def z_to_t(z: float, dof: np.ndarray) -> np.ndarray:
    """Inverse of t_to_z: the t-statistic needed to reach a given z (used for the displayed band)."""
    dof = np.maximum(dof, 1.0)
    c = (8 * dof + 1) / (8 * dof + 3)
    return np.sqrt(dof * np.expm1((z / c) ** 2 / dof))


def score_series(values: pd.Series, metric: str, cfg: DetectorConfig) -> pd.DataFrame:
    """Score one campaign's daily series for one metric against its own past.

    Two passes. Pass 1 scores every day against the raw past. Pass 2 re-scores
    with pass-1 anomalies removed from the history, so an ongoing outage can't
    "teach" the baseline that broken is normal. A permanent change still becomes
    the new normal, because pass 1 stops flagging it once it fills the window.
    """
    first = _score_against(values, values, metric, cfg)
    clean_history = values.mask(is_flagged(first, values, cfg))
    return _score_against(values, clean_history, metric, cfg)


def is_flagged(scored: pd.DataFrame, values: pd.Series, cfg: DetectorConfig) -> pd.Series:
    return (values.notna() & (scored["expected"] > 0)
            & (scored["score"].abs() >= cfg.z_threshold)
            & (scored["pct_change"].abs() >= cfg.min_pct_change))


def _score_against(values: pd.Series, history_source: pd.Series, metric: str,
                   cfg: DetectorConfig) -> pd.DataFrame:
    history = history_source.shift(1)  # only days strictly before the scored day -> no future leakage
    median, mad, count = rolling_baseline(history.to_numpy(dtype=float), cfg.window_days, cfg.min_history)
    expected = pd.Series(median, index=values.index)
    mad_sigma = pd.Series(MAD_TO_SIGMA * mad, index=values.index)

    if metric in COUNT_METRICS:
        # Counts: exact Poisson surprise, widened if this campaign is noisier than
        # pure randomness (overdispersion = observed variance / Poisson variance, >= 1).
        lam = expected.clip(lower=1e-9)
        dispersion = np.maximum(mad_sigma ** 2 / lam, 1.0)
        scale = np.sqrt(dispersion * lam)  # display band (normal approximation of the Poisson rule)
        obs, exp, disp = values.to_numpy(float), expected.to_numpy(float), dispersion.to_numpy(float)
        z = np.full(len(obs), np.nan)
        for i in np.flatnonzero(~np.isnan(obs) & (exp > 0)):
            z[i] = poisson_z(obs[i], exp[i]) / math.sqrt(disp[i])
        score = pd.Series(z, index=values.index)
    else:
        # Money and ratio metrics: robust t-score against the campaign's own MAD,
        # converted to an equivalent z because the MAD is estimated from few days.
        sigma = np.maximum(np.maximum(mad_sigma, cfg.rel_floor * expected.abs()), 1e-9)
        dof = MAD_EFFICIENCY * count - 1
        t = ((values - expected) / sigma).to_numpy(float)
        score = pd.Series(t_to_z(t, dof), index=values.index)
        # widen the displayed band so "outside the band" == "flagged"
        scale = sigma * z_to_t(cfg.z_threshold, dof) / cfg.z_threshold

    safe_expected = expected.where(expected > 0)
    return pd.DataFrame({
        "expected": expected,
        "lower": (expected - cfg.z_threshold * scale).clip(lower=0),
        "upper": expected + cfg.z_threshold * scale,
        "score": score,
        "pct_change": (values - safe_expected) / safe_expected,
        "history_points": count,
    }, index=values.index)


def classify_severity(score: float, pct_change: float, metric: str, cfg: DetectorConfig) -> str:
    if abs(score) >= cfg.critical_z:
        return "critical"
    # Severe delivery collapse on spend, impressions, or clicks is critical (e.g. budget exhaustion)
    if metric in ("spend", "impressions", "clicks") and pct_change <= -0.90:
        return "critical"
    # Volume metrics collapsing by >= 90% are only critical if statistically extreme (high_z),
    # preventing low-volume zero-conversion variance from firing false critical alarms
    if metric in VOLUME_METRICS and pct_change <= -0.90 and abs(score) >= cfg.high_z:
        return "critical"
    if abs(score) >= cfg.high_z:
        return "high"
    if metric in VOLUME_METRICS and pct_change <= -MAJOR_VOLUME_CHANGE:  # breakages show up as drops
        return "high"
    return "medium"


def detect(frame: pd.DataFrame, metrics: list[str], cfg: DetectorConfig) -> DetectionResult:
    score_parts = []
    anomalies: list[Anomaly] = []
    for campaign_id, rows in frame.groupby("campaign_id", sort=True):
        rows = rows.sort_values("date")
        med_conv = rows["conversions"].median() if "conversions" in rows.columns else 999.0
        for metric in metrics:
            observed = rows[metric].astype(float)
            s = score_series(observed, metric, cfg)
            s.insert(0, "observed", observed)
            s.insert(0, "metric", metric)
            s.insert(0, "date", rows["date"])
            s.insert(0, "campaign_id", campaign_id)
            s["is_anomaly"] = is_flagged(s, observed, cfg)
            # Low-volume revenue guard: If a campaign averages <= 2 conversions/day,
            # an occasional day with 0 conversions and 0 revenue is normal Poisson noise,
            # not an actionable revenue anomaly.
            if metric == "revenue":
                zero_revenue = (observed == 0) & (med_conv <= 2)
                s.loc[zero_revenue, "is_anomaly"] = False
            score_parts.append(s)
            for r in s[s["is_anomaly"]].itertuples(index=False):
                anomalies.append(Anomaly(
                    campaign_id=str(campaign_id), date=r.date, metric=metric,
                    observed=float(r.observed), expected=float(r.expected),
                    lower=float(r.lower), upper=float(r.upper), score=float(r.score),
                    pct_change=float(r.pct_change), direction="up" if r.score > 0 else "down",
                    severity=classify_severity(r.score, r.pct_change, metric, cfg),
                    history_points=int(r.history_points),
                    method="rolling_median_poisson" if metric in COUNT_METRICS else "rolling_median_mad",
                ))
    scores = pd.concat(score_parts, ignore_index=True) if score_parts else pd.DataFrame(
        columns=["campaign_id", "date", "metric", "observed", "expected", "lower", "upper",
                 "score", "pct_change", "history_points", "is_anomaly"])
    return DetectionResult(anomalies=anomalies, scores=scores)
