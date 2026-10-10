"""
generate_data.py

Ingests the PS-04 dataset (PS-04_campaign_anomaly_alerting/daily_campaign_metrics.csv)
into SQLite (data/campaign_data.db) as the primary dataset. Also computes derived
metrics (CTR, CVR, CPC, ROAS) for fast downstream query performance.
"""

import os
import sys
import sqlite3
import numpy as np
import pandas as pd

CSV_PATH = "PS-04_campaign_anomaly_alerting/daily_campaign_metrics.csv"
DB_PATH = "data/campaign_data.db"


def load_and_preprocess_ps04_data(csv_path: str = CSV_PATH) -> pd.DataFrame:
    """Loads daily_campaign_metrics.csv and computes derived advertising metrics."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}")

    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    df["timestamp"] = df["date"]  # compatibility alias

    # Derived metrics
    df["ctr"] = (df["clicks"] / df["impressions"].replace(0, np.nan)).fillna(0.0).round(5)
    df["cvr"] = (df["conversions"] / df["clicks"].replace(0, np.nan)).fillna(0.0).round(5)
    df["cpc"] = (df["spend"] / df["clicks"].replace(0, np.nan)).fillna(0.0).round(2)
    df["cpa"] = (df["spend"] / df["conversions"].replace(0, np.nan)).fillna(0.0).round(2)
    df["roas"] = (df["revenue"] / df["spend"].replace(0, np.nan)).fillna(0.0).round(2)
    df["day_of_week"] = df["date"].dt.day_name()
    df["is_weekend"] = df["date"].dt.dayofweek >= 5

    return df


def sync_to_db(df: pd.DataFrame, db_path: str = DB_PATH):
    """Saves DataFrame into SQLite table campaign_metrics."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    # Convert datetime to string for SQLite compatibility
    save_df = df.copy()
    save_df["date"] = save_df["date"].dt.strftime("%Y-%m-%d")
    save_df["timestamp"] = save_df["timestamp"].dt.strftime("%Y-%m-%d")
    save_df.to_sql("campaign_metrics", conn, if_exists="replace", index=False)
    conn.close()


def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    print(f"Loading PS-04 dataset from {CSV_PATH}...")
    df = load_and_preprocess_ps04_data(CSV_PATH)
    sync_to_db(df, DB_PATH)

    print(f"Successfully loaded {len(df)} rows across {df['campaign_id'].nunique()} campaigns into {DB_PATH}.")
    print(f"Date range: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')} (180 days).")
    print(f"Verticals: Ecommerce ({len(df[df['vertical']=='ecommerce'])} rows), B2B ({len(df[df['vertical']=='b2b'])} rows)")
    print(f"Landing page groups: {sorted(df['landing_page_group'].unique())}")


if __name__ == "__main__":
    main()
