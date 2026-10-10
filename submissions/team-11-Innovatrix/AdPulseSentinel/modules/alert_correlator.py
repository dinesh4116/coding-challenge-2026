def correlate_alerts(alerts):
    incidents = {}

    severity_rank = {
        "Low": 1,
        "Medium": 2,
        "High": 3
    }

    for alert in alerts:
        campaign = alert["campaign"]

        if campaign not in incidents:
            incidents[campaign] = {
                "campaign": campaign,
                "severity": alert["severity"],
                "alerts": [],
                "evidence": [],
                "repeat_count": 0
            }

        incident = incidents[campaign]

        # Avoid duplicate alerts of the same type
        if alert["type"] not in incident["alerts"]:
            incident["alerts"].append(alert["type"])
            incident["evidence"].append(alert["evidence"])
        else:
            incident["repeat_count"] += 1

        # Keep the highest severity
        if severity_rank[alert["severity"]] > severity_rank[incident["severity"]]:
            incident["severity"] = alert["severity"]

    return list(incidents.values())