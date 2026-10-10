
import time
from datetime import datetime

from database import get_connection, initialize_database


def setup_tracking():
    initialize_database()

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_events (
                event_type TEXT NOT NULL,
                event_id INTEGER NOT NULL,
                PRIMARY KEY (event_type, event_id)
            )
        """)


def create_incident(conn, campaign, severity, description):
    conn.execute("""
        INSERT INTO incidents
        (campaign, severity, description, status, event_time)
        VALUES (?, ?, ?, 'Open', ?)
    """, (
        campaign,
        severity,
        description,
        datetime.now().isoformat(timespec="seconds")
    ))

    print(f"[ALERT] {severity} | {campaign} | {description}")


def process_campaign_events(conn):
    rows = conn.execute("""
        SELECT id, campaign, spend, clicks, conversions
        FROM campaign_events
        WHERE id NOT IN (
            SELECT event_id FROM processed_events
            WHERE event_type = 'campaign'
        )
        ORDER BY id
    """).fetchall()

    for event_id, campaign, spend, clicks, conversions in rows:
        if spend > 5000:
            create_incident(
                conn, campaign, "High",
                f"Spending spike: ₹{spend:.2f} exceeded ₹5000."
            )

        if clicks > 100:
            create_incident(
                conn, campaign, "High",
                f"Unusual click activity: {clicks} clicks detected."
            )

        if conversions < 10:
            create_incident(
                conn, campaign, "Medium",
                f"Low conversions detected: {conversions}."
            )

        conn.execute("""
            INSERT OR IGNORE INTO processed_events
            (event_type, event_id) VALUES ('campaign', ?)
        """, (event_id,))


def process_security_events(conn):
    rows = conn.execute("""
        SELECT id, campaign, clicks_per_minute, repeated_requests
        FROM security_events
        WHERE id NOT IN (
            SELECT event_id FROM processed_events
            WHERE event_type = 'security'
        )
        ORDER BY id
    """).fetchall()

    for event_id, campaign, clicks, repeated in rows:
        if clicks > 100:
            create_incident(
                conn, campaign, "High",
                f"Suspicious click burst: {clicks} clicks per minute."
            )

        if repeated > 50:
            create_incident(
                conn, campaign, "Medium",
                f"Repeated request pattern: {repeated} requests."
            )

        conn.execute("""
            INSERT OR IGNORE INTO processed_events
            (event_type, event_id) VALUES ('security', ?)
        """, (event_id,))


def run_detector():
    setup_tracking()
    print("AdPulse Sentinel automatic detector started.")
    print("Checking for new events every 5 seconds.")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            with get_connection() as conn:
                process_campaign_events(conn)
                process_security_events(conn)

            time.sleep(5)

    except KeyboardInterrupt:
        print("\nAutomatic detector stopped.")


if __name__ == "__main__":
    run_detector()
