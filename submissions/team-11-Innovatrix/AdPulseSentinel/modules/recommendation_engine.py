def generate_recommendations(incident):
    recommendations = []

    for alert in incident["alerts"]:
        if alert == "Spending Spike":
            recommendations.append(
                "Review campaign budget, bids, and recent spend changes."
            )

        elif alert == "Unusual Click Activity":
            recommendations.append(
                "Check click trends and verify campaign traffic sources."
            )

        elif alert == "Low Conversions":
            recommendations.append(
                "Inspect the landing page, conversion tracking, and user journey."
            )

        elif alert == "Suspicious Click Burst":
            recommendations.append(
                "Investigate traffic sources, request timing, and possible automated clicks."
            )

        elif alert == "Repeated Request Pattern":
            recommendations.append(
                "Review repeated requests and investigate the source before taking action."
            )

    if not recommendations:
        recommendations.append(
            "Continue monitoring and review new evidence."
        )

    return list(dict.fromkeys(recommendations))