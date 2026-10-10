def create_incident(alerts):
    return {
        "incidents": alerts,
        "status": {
            incident["campaign"]: "Open"
            for incident in alerts
        }
    }


def resolve_incident(manager, campaign):
    if campaign in manager["status"]:
        manager["status"][campaign] = "Resolved"

    return manager


def get_open_incidents(manager):
    return [
        incident
        for incident in manager["incidents"]
        if manager["status"].get(
            incident["campaign"], "Open"
        ) == "Open"
    ]