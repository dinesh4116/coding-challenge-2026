"""Plain-English explanations and first diagnostic steps.

Explanations describe what changed against which baseline. They never claim a
root cause: an anomaly is a statistical signal, and the action is a first check.
"""
from __future__ import annotations

import pandas as pd

LABEL = {"spend": "Spend", "impressions": "Impressions", "clicks": "Clicks",
         "conversions": "Conversions", "ctr": "Click-through rate", "cvr": "Conversion rate",
         "revenue": "Revenue"}

ACTIONS = {
    ("spend", "up"): "Check budget caps, recent bid or bid-strategy changes, and pacing settings.",
    ("spend", "down"): "Check whether the budget was exhausted, the campaign paused, or billing failed.",
    ("revenue", "up"): "Check for a tracking or currency misconfiguration before crediting a real gain.",
    ("revenue", "down"): "Check conversion tracking and order/lead values first, then the checkout or form flow.",
    ("impressions", "up"): "Check for targeting or audience expansion and recent bid increases.",
    ("impressions", "down"): "Check delivery status, ad approvals, targeting changes and budget limits.",
    ("clicks", "up"): "Check traffic sources for invalid or bot clicks.",
    ("clicks", "down"): "Check ad disapprovals, creative changes and placement mix.",
    ("conversions", "up"): "Check for duplicate conversion-tag firing before trusting the gain.",
    ("conversions", "down"): "Verify the conversion tag is firing on the confirmation page, then check the landing page.",
    ("ctr", "up"): "Check for invalid traffic or a change in placement mix.",
    ("ctr", "down"): "Review creative fatigue, ad disapprovals, and placement or audience changes.",
    ("cvr", "up"): "Check for duplicate conversion counting or a changed conversion definition.",
    ("cvr", "down"): "Check conversion tracking first, then landing-page speed, errors and checkout flow.",
}


def _fmt(metric: str, v: float) -> str:
    if pd.isna(v):
        return "n/a"
    if metric in ("ctr", "cvr"):
        return f"{v * 100:.2f}%"
    if metric in ("spend", "revenue"):
        return f"{v:,.2f}"
    return f"{v:,.0f}"


def explain_row(r) -> str:
    who = f"{LABEL[r.metric]} for {r.campaign_id} on {pd.Timestamp(r.date).date()}"
    if r.status == "missing_value":
        return f"{who}: no value recorded, so it was not scored. Check the data feed."
    if r.status == "insufficient_history":
        return (f"{who}: only {int(r.n_history)} days of usable history "
                f"(fewer than required), so no baseline was set.")
    base = (f"{who} was {_fmt(r.metric, r.observed)} against an expected "
            f"{_fmt(r.metric, r.baseline)} (weekday-adjusted median of the previous "
            f"{int(r.n_history)} days)")
    if pd.notna(r.pct_change):
        base += f", a {abs(r.pct_change) * 100:.0f}% {'rise' if r.pct_change > 0 else 'drop'}"
    base += f"; robust z = {r.z:+.1f}."
    if not r.is_anomaly:
        return base + " Within this campaign's normal range."
    return (base + f" Evidence strength {r.evidence_score:.2f} (heuristic, not a probability). "
            "This is unusual for this campaign; it does not by itself confirm the cause.")


def add_explanations(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["explanation"] = [explain_row(r) for r in df.itertuples(index=False)]
    df["diagnostic_action"] = [ACTIONS.get((m, d), "") if a else ""
                               for m, d, a in zip(df["metric"], df["direction"], df["is_anomaly"])]
    return df
