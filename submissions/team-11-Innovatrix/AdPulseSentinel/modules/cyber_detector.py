def detect_cyber_threats(data):
    alerts = []

    for _, row in data.iterrows():
        if row["clicks_per_minute"] > 100:
            alerts.append({
                "campaign": row["campaign"],
                "type": "Suspicious Click Burst",
                "severity": "High",
                "evidence": (
                    f"{row['clicks_per_minute']} clicks per minute "
                    "exceeded the threshold of 100."
                )
            })

        if row["repeated_requests"] > 50:
            alerts.append({
                "campaign": row["campaign"],
                "type": "Repeated Request Pattern",
                "severity": "Medium",
                "evidence": (
                    f"{row['repeated_requests']} repeated requests "
                    "exceeded the threshold of 50."
                )
            })

    return alerts