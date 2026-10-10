
from database import get_connection

with get_connection() as conn:
    total = conn.execute(
        "SELECT COUNT(*) FROM campaign_events"
    ).fetchone()[0]

    print("Total saved campaign events:", total)

    rows = conn.execute("""
        SELECT campaign, spend, clicks, conversions, event_time
        FROM campaign_events
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

    print("\nLatest 5 events:")
    for row in rows:
        print(row)
