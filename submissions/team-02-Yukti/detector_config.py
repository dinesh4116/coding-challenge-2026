"""Configurable thresholds for the Adomaly detection engine.

Defaults are starting values. Any tuning must be done on the development
period only (see src/config.py), never on the held-out evaluation period.
"""
from __future__ import annotations

from dataclasses import dataclass, field

BASE_METRICS = ("spend", "impressions", "clicks", "conversions")
# Derived ratios: (numerator, denominator). They isolate rate problems from volume changes.
RATIO_METRICS = {"ctr": ("clicks", "impressions"), "cvr": ("conversions", "clicks")}
# Metrics scored on log1p scale (multiplicative noise); ratios stay on raw scale.
# "revenue" is only present in the PS-04 supplied dataset (see src/config.py);
# it is monetary like spend, so it belongs on the same log1p scale. Adding it
# here does not affect the synthetic benchmark, which never has a revenue column.
LOG_METRICS = set(BASE_METRICS) | {"revenue"}

# Metrics tuple for the PS-04 supplied dataset: base metrics + revenue + ratios.
PS04_BASE_METRICS = BASE_METRICS + ("revenue",)


@dataclass(frozen=True)
class DetectorConfig:
    metrics: tuple = BASE_METRICS + tuple(RATIO_METRICS)

    # Baseline
    window: int = 28            # trailing days used for median / MAD
    min_history: int = 14       # fewer valid days -> no score (insufficient history)
    weekday_adjust: bool = True
    weekday_groups: str = "weekend"  # "weekend" (Sat-Sun vs Mon-Fri) or "dow" (7 groups)
    weekday_lookback: int = 56  # trailing days used to estimate weekday offsets
    weekday_min_obs: int = 3    # per group, else offset = 0
    scale_floor_log: float = 0.02   # min robust scale on log1p scale (~2% relative)
    scale_floor_ratio: float = 0.02  # min robust scale as fraction of ratio baseline
    abs_scale_floor: float = 1e-6

    # Anomaly and severity (|robust z|)
    # Chosen on the DEV period only: 3.5 -> 75 dev false flags, 4.0 -> 38, 4.5 -> 18;
    # all four dev incidents were flagged at each value.
    z_threshold: float = 4.0
    severity_bands: tuple = (6.0, 9.0)  # 4-6 low, 6-9 medium, >=9 high

    # Evidence strength (heuristic in [0, 1], NOT a probability)
    z_full: float = 10.0        # |z| at which magnitude component saturates at 1
    min_denominator: dict = field(default_factory=lambda: {"ctr": 1000, "cvr": 50})

    # Routing
    # With full history and quality, |z| 4-5 (borderline) goes to Human Review, >=5 to Alert.
    alert_evidence: float = 0.5  # anomalous & evidence >= this -> Alert, else Human Review

    # Episodes
    max_gap_days: int = 1        # quiet days allowed inside one episode
