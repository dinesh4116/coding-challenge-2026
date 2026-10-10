"""
alerting.py

Handles dispatching anomaly alerts to external notification channels (e.g., Slack webhook)
with rich formatting and executive plain-English summaries.
"""

import os
import requests
import pandas as pd

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")


def send_slack_alert(alert_row: pd.Series):
    """
    Sends a formatted alert to a Slack webhook based on incident details.
    """
    channel = alert_row.get("channel", "Unknown Channel")
    campaign = alert_row.get("campaign_name", alert_row.get("campaign", "Unknown Campaign"))
    incident_type = alert_row.get("incident_type", alert_row.get("metric", "Anomaly"))
    severity = alert_row.get("severity", "HIGH")
    date_str = alert_row.get("date", alert_row.get("timestamp", "Unknown Date"))
    change_pct = alert_row.get("change_pct", "")
    actual_val = alert_row.get("actual_value", alert_row.get("value", ""))
    normal_val = alert_row.get("normal_baseline", alert_row.get("rolling_mean", ""))
    explanation = alert_row.get("explanation", "Performance anomaly detected.")
    recommended_action = alert_row.get("recommended_action", "Investigate campaign delivery and tracking.")

    if not SLACK_WEBHOOK_URL:
        # Mock / local terminal dispatch
        print(f"[Alert] [{severity}] Would send to Slack: {channel} | {campaign}")
        print(f"        Incident: {incident_type} ({change_pct}) on {date_str}")
        print(f"        Summary : {explanation}")
        print(f"        Action  : {recommended_action}\n")
        return

    color = "#D50000" if severity == "CRITICAL" else "#FF6D00"
    title = f"🚨 [{severity}] {incident_type}: {channel} | {campaign}"

    text = (
        f"*Date:* {date_str}\n"
        f"*Magnitude:* `{change_pct}` ({actual_val} vs Normal: {normal_val})\n"
        f"*Diagnosis:* {explanation}\n"
        f"*Recommended Action:* {recommended_action}\n"
    )

    payload = {
        "attachments": [
            {
                "fallback": title,
                "color": color,
                "title": title,
                "text": text,
                "footer": "PS-04 Campaign Anomaly Alerting Engine",
            }
        ]
    }

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        print(f"Successfully dispatched Slack alert for {campaign} on {date_str}.")
    except Exception as e:
        print(f"Failed to send Slack alert: {e}")
