
import pandas as pd
import math

def triage(row):
    clicks = max(0, float(row["clicks"]))
    conversions = max(0, float(row["conversions"]))
    cost = max(0, float(row["cost"]))
    value = max(0, float(row["conversion_value"]))

    # Use a conservative estimate of conversion rate.
    # This avoids trusting tiny samples.
    n = max(clicks, conversions)
    p = min(conversions / n, 1) if n else 0
    z = 1.96

    if n > 0:
        lower = (
            p + z*z/(2*n)
            - z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
        ) / (1 + z*z/n)
    else:
        lower = 0

    if clicks < 20:
        return pd.Series([
            "IGNORE", "Low",
            "Insufficient clicks for a reliable decision",
            "YES"
        ])

    if clicks >= 30 and conversions >= 5 and value > cost and lower >= 0.03:
        return pd.Series([
            "PROMOTE", "High",
            "Sufficient conversion evidence and positive observed return",
            "NO"
        ])

    if clicks >= 80 and conversions == 0 and cost > 0:
        return pd.Series([
            "BLOCK", "Medium",
            "High click volume with zero conversions; review before blocking",
            "YES"
        ])

    return pd.Series([
        "IGNORE", "Low",
        "Evidence is insufficient or performance is inconclusive",
        "YES"
    ])


def analyze(df):
    required = ["clicks", "cost", "conversions", "conversion_value"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))

    result = df.copy()

    for col in required:
        result[col] = pd.to_numeric(
            result[col], errors="coerce"
        )

    invalid = result[required].isna().any(axis=1)
    invalid |= (result[required] < 0).any(axis=1)
    invalid |= result["conversions"] > result["clicks"]

    safe = result.copy()
    safe[required] = safe[required].fillna(0).clip(lower=0)

    output = safe.apply(triage, axis=1)
    output.columns = [
        "decision", "confidence", "reason", "human_review"
    ]

    result = pd.concat([result, output], axis=1)

    result.loc[invalid, "decision"] = "IGNORE"
    result.loc[invalid, "confidence"] = "Low"
    result.loc[invalid, "reason"] = "Invalid or missing metric values"
    result.loc[invalid, "human_review"] = "YES"

    return result
