
import random
import time
from datetime import datetime

from database import get_connection, initialize_database

CAMPAIGNS = [
    "Summer Sale",
    "Student Offer",
    "Tech Products",
    "Travel Ads",
]

def generate_event():
    campaign = random.choice(CAMPAIGNS)

    # Generate normal or suspicious activity
    suspicious = random.random() < 0.25

    if suspicious:
        clicks = random.randint(150, 300)
        repeated_requests = random.randint(55, 100)
    else:
        clicks = random.randint(10, 80)
        repeated_requests = random.randint(5, 40)

    spend = round(random.uniform(500, 9000), 2)
    conversions = random.randint(0, 80)
    event_time = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO campaign_events
            (campaign, spend, clicks, conversions, event_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (campaign, spend, clicks, conversions, event_time),
        )

        conn.execute(
            """
            INSERT INTO security_events
            (campaign, clicks_per_minute, repeated_requests, event_time)
            VALUES (?, ?, ?, ?)
            """,
            (campaign, clicks, repeated_requests, event_time),
        )

    print(
        f"[{event_time}] New event | {campaign} | "
        f"Spend: ₹{spend} | Clicks: {clicks} | "
        f"Repeated requests: {repeated_requests}"
    )


if __name__ == "__main__":
    initialize_database()
    print("AdPulse Sentinel automatic generator started!")
    print("Generating a new event every 5 seconds.")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            generate_event()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nAutomatic generator stopped.")
