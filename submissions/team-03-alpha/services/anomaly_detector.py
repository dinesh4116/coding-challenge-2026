import pandas as pd
from .baseline import build, WINDOW, MIN_HISTORY
from .severity import classify
from .recommendation import advise

Z_THRESHOLD = 3.5   # statistical significance (robust z-score)
MIN_PCT = 0.25      # and a meaningful business change
MIN_VOLUME = 5      # ignore tiny-count metrics (too noisy)
BAD_DIRECTION = {"spend": "up", "clicks": "down", "ctr": "down", "conversions": "down", "revenue": "down"}

def _alert(row, metric, kind, observed, expected, z, pct, sev):
    why, fix = advise(metric, kind)
    sign = "+" if pct >= 0 else ""
    return {"metric_date": row["metric_date"], "metric": metric,
            "alert_type": "spike" if kind == "up" else ("tracking" if kind == "tracking" else
                          "budget" if kind == "budget" else "drop"),
            "severity": sev, "observed": round(float(observed), 2), "expected": round(float(expected), 2),
            "z_score": round(float(z), 2), "pct_change": round(float(pct), 4),
            "explanation": f"{why} Observed {observed:,.2f} vs expected {expected:,.2f} ({sign}{pct*100:.0f}%).",
            "recommendation": fix}

def detect(df):
    """df: one campaign's daily rows. Returns a list of alert dicts (campaign_id added by caller)."""
    df = df.sort_values("metric_date").reset_index(drop=True).copy()
    for c in ("spend", "impressions", "clicks", "conversions", "revenue", "budget"):
        df[c] = df[c].astype(float)
    df["ctr"] = (df["clicks"] / df["impressions"].where(df["impressions"] > 0) * 100).fillna(0)
    df["weekday"] = pd.to_datetime(df["metric_date"]).dt.weekday
    out, last = [], {}
    for i in range(MIN_HISTORY, len(df)):
        row, hist = df.iloc[i], df.iloc[max(0, i - WINDOW):i]
        wd, flagged = int(row["weekday"]), set()
        # Rule 1: tracking failure (traffic normal, zero conversions)
        bc, bk = build(hist, "conversions", wd), build(hist, "clicks", wd)
        if bc["median"] >= 3 and row["conversions"] == 0 and row["clicks"] >= 0.5 * bk["median"]:
            out.append(_alert(row, "conversions", "tracking", 0, bc["median"], -bc["median"] / bc["scale"], -1.0, "critical"))
            flagged.add("conversions")
        # Rule 2: unexpected budget exhaustion
        ratio = (hist["spend"] / hist["budget"].where(hist["budget"] > 0)).dropna()
        if row["budget"] > 0 and len(ratio) and row["spend"] >= 0.98 * row["budget"] and ratio.median() < 0.85:
            out.append(_alert(row, "spend", "budget", row["spend"], ratio.median() * row["budget"], 0, 0.0, "high"))
            flagged.add("spend")
        # Rule 3: statistical deviation from this campaign's own baseline
        for m, direction in BAD_DIRECTION.items():
            if m in flagged or (m == "revenue" and "conversions" in flagged):
                continue
            b = build(hist, m, wd)
            if m in ("clicks", "conversions", "revenue") and b["median"] < MIN_VOLUME:
                continue
            z = (row[m] - b["median"]) / b["scale"]
            pct = (row[m] - b["median"]) / b["median"] if b["median"] else 0
            bad = z >= Z_THRESHOLD if direction == "up" else z <= -Z_THRESHOLD
            if bad and abs(pct) >= MIN_PCT:
                flagged.add(m)
                streak = last.get(m) == i - 1      # same ongoing incident -> don't re-alert daily
                last[m] = i
                if not streak:
                    out.append(_alert(row, m, direction, row[m], b["median"], z, pct, classify(z, pct)))
    return out
