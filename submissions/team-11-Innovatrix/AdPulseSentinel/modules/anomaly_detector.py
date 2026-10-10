import pandas as pd


def detect_campaign_anomalies(data):
    alerts = []

    for _, row in data.iterrows():
        if row["spend"] > row["spend_limit"]:
            alerts.append({
                "campaign": row["campaign"],
                "type": "Spending Spike",
                "severity": "High",
                "evidence": f"Spend reached ₹{row['spend']}, above the limit of ₹{row['spend_limit']}."
            })

        if row["clicks"] > row["click_limit"]:
            alerts.append({
                "campaign": row["campaign"],
                "type": "Unusual Click Activity",
                "severity": "Medium",
                "evidence": f"Clicks reached {row['clicks']}, above the limit of {row['click_limit']}."
            })

        if row["conversions"] < row["conversion_min"]:
            alerts.append({
                "campaign": row["campaign"],
                "type": "Low Conversions",
                "severity": "Medium",
                "evidence": f"Conversions fell to {row['conversions']}."
            })

    return alerts