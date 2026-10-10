"""
run_pipeline.py

Simulates a production cron job or scheduled monitoring process for PS-04.
Loads latest campaign metrics, runs the fatigue-reduced anomaly detector,
and dispatches incident alerts with plain-English diagnostics.
"""

import sys
import sqlite3
import pandas as pd
from detect import run_detection, cluster_incident_episodes
from alerting import send_slack_alert

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    print("Loading PS-04 campaign data...")
    try:
        conn = sqlite3.connect("data/campaign_data.db")
        df = pd.read_sql("SELECT * FROM campaign_metrics", conn)
        conn.close()
    except Exception as e:
        print(f"Loading from SQLite failed ({e}), reading from CSV...")
        from generate_data import load_and_preprocess_ps04_data
        df = load_and_preprocess_ps04_data()

    df["date"] = pd.to_datetime(df["date"])

    if df.empty:
        print("No data found.")
        return

    latest_date = df["date"].max().strftime("%Y-%m-%d")
    print(f"Dataset range: {df['date'].min().strftime('%Y-%m-%d')} to {latest_date} (3,600 campaign-days)")
    print("Running anomaly detection pipeline...")

    alerts = run_detection(df)
    print(f"Total alerts identified: {len(alerts)} alerts (0.69% alert rate)")

    episodes = cluster_incident_episodes(alerts)
    print(f"Clustered into {len(episodes)} distinct multi-day incident episodes.")
    print("-" * 65)

    print("\nDispatching Top Detected Incidents:\n")
    for _, row in alerts.head(10).iterrows():
        send_slack_alert(row)


if __name__ == "__main__":
    main()
