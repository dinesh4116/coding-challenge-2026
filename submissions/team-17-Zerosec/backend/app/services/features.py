"""Derived ratio metrics (CTR, CVR, CPC, CPA, ROAS).

A ratio is only added when both of its inputs exist in the dataset. A ratio
on a tiny denominator (e.g. CVR from 3 clicks) is noise, so it is left
missing (NaN) below MIN_DENOMINATOR. This is the low-volume guard for ratios,
and it also means a zero denominator can never produce infinity.
"""
import pandas as pd

# metric -> (numerator, denominator)
DERIVED_METRICS: dict[str, tuple[str, str]] = {
    "ctr": ("clicks", "impressions"),
    "cvr": ("conversions", "clicks"),
    "cpc": ("spend", "clicks"),
    "cpa": ("spend", "conversions"),
    "roas": ("revenue", "spend"),
}
MIN_DENOMINATOR = {"ctr": 500, "cvr": 30, "cpc": 30, "cpa": 3, "roas": 20.0}


def add_derived_metrics(frame: pd.DataFrame, metrics: list[str]) -> tuple[pd.DataFrame, list[str]]:
    out = frame.copy()
    added = []
    for name, (num, den) in DERIVED_METRICS.items():
        if num in metrics and den in metrics:
            denominator = out[den].where(out[den] >= MIN_DENOMINATOR[name])
            out[name] = out[num] / denominator
            added.append(name)
    return out, added
