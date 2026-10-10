def calculate_risk(incident):
    score = 0

    severity_points = {
        "Low": 20,
        "Medium": 50,
        "High": 80
    }

    score += severity_points.get(incident["severity"], 0)

    if any("Suspicious" in alert or "Repeated" in alert
           for alert in incident["alerts"]):
        score += 15

    if len(incident["alerts"]) >= 2:
        score += 10

    return min(score, 100)


def get_risk_level(score):
    if score >= 75:
        return "High"
    elif score >= 40:
        return "Medium"
    else:
        return "Low"