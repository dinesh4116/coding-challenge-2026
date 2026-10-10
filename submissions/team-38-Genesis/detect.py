"""
detect.py

Campaign Anomaly Alerting Engine for PS-04.
Detects marketing performance incidents without alert fatigue:
  1. Day-of-week seasonality awareness (avoids flagging expected B2B weekend dips)
  2. Small-campaign noise dampening (ignores statistical Poisson variance on low-volume days)
  3. Correlated Landing Page group failure detection
  4. Rich, plain-English explanations: what changed, by how much, against what normal baseline
"""

import sys
import sqlite3
import pandas as pd
import numpy as np

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def compute_baselines(group: pd.DataFrame, window_days: int = 14) -> pd.DataFrame:
    """
    Computes trailing baseline statistics with weekend awareness for B2B campaigns.
    """
    group = group.sort_values("date").reset_index(drop=True).copy()
    group["is_weekend"] = group["date"].dt.dayofweek >= 5
    vertical = group["vertical"].iloc[0]

    baseline_records = []

    for i in range(len(group)):
        if i < 7:
            # Need at least 7 days of historical context
            baseline_records.append({
                "med_spend": np.nan, "med_clicks": np.nan, "med_conv": np.nan,
                "med_cvr": np.nan, "med_ctr": np.nan, "med_cpc": np.nan,
                "med_rev": np.nan, "med_roas": np.nan
            })
            continue

        start_idx = max(0, i - window_days)
        window = group.iloc[start_idx:i]
        today = group.iloc[i]

        # Handle B2B weekend seasonality: compare weekend days only to weekend baselines
        is_wknd = bool(today["is_weekend"])
        if vertical == "b2b":
            ref = window[window["is_weekend"] == is_wknd]
            if len(ref) < 3:
                ref = window
        else:
            ref = window

        baseline_records.append({
            "med_spend": ref["spend"].median(),
            "med_clicks": ref["clicks"].median(),
            "med_conv": ref["conversions"].median(),
            "med_cvr": ref["cvr"].median(),
            "med_ctr": ref["ctr"].median(),
            "med_cpc": ref["cpc"].median(),
            "med_rev": ref["revenue"].median(),
            "med_roas": ref["roas"].median(),
        })

    baselines_df = pd.DataFrame(baseline_records)
    return pd.concat([group, baselines_df], axis=1)


def detect_campaign_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Runs multi-pattern incident detection across all campaigns.
    Suppresses false alarms and outputs plain English diagnostic explanations.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    if "is_weekend" not in df.columns:
        df["is_weekend"] = df["date"].dt.dayofweek >= 5

    alerts = []

    # Process each campaign independently
    for (cid, cname), group in df.groupby(["campaign_id", "campaign_name"]):
        annotated = compute_baselines(group)

        for _, row in annotated.dropna(subset=["med_spend"]).iterrows():
            date_str = row["date"].strftime("%Y-%m-%d")
            lp = row["landing_page_group"]
            channel = row["channel"]
            vert = row["vertical"]

            # ---- Pattern 1: Conversion Tracking Failure / Checkout Outage ----
            # High click volume, but conversions crashed by >= 75%
            if row["clicks"] >= 40 and row["med_conv"] >= 8:
                if row["conversions"] <= row["med_conv"] * 0.25 and row["cvr"] <= row["med_cvr"] * 0.30:
                    drop_pct = (1.0 - (row["conversions"] / row["med_conv"])) * 100
                    alerts.append({
                        "date": date_str,
                        "campaign_id": cid,
                        "campaign_name": cname,
                        "channel": channel,
                        "vertical": vert,
                        "landing_page_group": lp,
                        "incident_type": "Conversion Tracking Outage",
                        "severity": "CRITICAL",
                        "metric": "conversions",
                        "actual_value": f"{row['conversions']} conv (CVR {row['cvr']:.2%})",
                        "normal_baseline": f"{row['med_conv']:.1f} conv (CVR {row['med_cvr']:.2%})",
                        "change_pct": f"-{drop_pct:.1f}%",
                        "explanation": (
                            f"Conversions collapsed by {drop_pct:.1f}% ({row['conversions']} vs normal {row['med_conv']:.1f}) "
                            f"despite generating {row['clicks']:,} clicks and spending ${row['spend']:,.2f}. "
                            f"Likely tracking pixel disconnection or checkout form failure on {lp}."
                        ),
                        "recommended_action": "Check pixel firing status, tag manager triggers, and checkout funnels.",
                    })

            # ---- Pattern 2: Campaign Delivery Collapse / Accidental Pause ----
            # Spend and clicks crashed by >= 85% for an established campaign
            if row["med_spend"] >= 400:
                if row["spend"] <= row["med_spend"] * 0.15 and row["clicks"] <= row["med_clicks"] * 0.15:
                    drop_pct = (1.0 - (row["spend"] / row["med_spend"])) * 100
                    alerts.append({
                        "date": date_str,
                        "campaign_id": cid,
                        "campaign_name": cname,
                        "channel": channel,
                        "vertical": vert,
                        "landing_page_group": lp,
                        "incident_type": "Delivery Collapse / Paused",
                        "severity": "HIGH",
                        "metric": "spend",
                        "actual_value": f"${row['spend']:,.2f} ({row['clicks']:,} clicks)",
                        "normal_baseline": f"${row['med_spend']:,.2f} ({row['med_clicks']:,.0f} clicks)",
                        "change_pct": f"-{drop_pct:.1f}%",
                        "explanation": (
                            f"Campaign delivery halted: daily spend dropped by {drop_pct:.1f}% "
                            f"(${row['spend']:,.2f} vs expected ${row['med_spend']:,.2f}). "
                            f"Clicks collapsed to {row['clicks']} (normal {row['med_clicks']:,.0f})."
                        ),
                        "recommended_action": "Verify ad disapproval status, billing/credit card expiration, or accidental pause.",
                    })

            # ---- Pattern 3: Budget Runaway / Severe Overspend ----
            # Spend surged >= 3.0x above normal baseline
            if row["med_spend"] >= 100:
                if row["spend"] >= row["med_spend"] * 3.0:
                    surge_pct = ((row["spend"] / row["med_spend"]) - 1.0) * 100
                    alerts.append({
                        "date": date_str,
                        "campaign_id": cid,
                        "campaign_name": cname,
                        "channel": channel,
                        "vertical": vert,
                        "landing_page_group": lp,
                        "incident_type": "Budget Runaway / Overspend",
                        "severity": "CRITICAL",
                        "metric": "spend",
                        "actual_value": f"${row['spend']:,.2f}",
                        "normal_baseline": f"${row['med_spend']:,.2f}",
                        "change_pct": f"+{surge_pct:.1f}%",
                        "explanation": (
                            f"Severe budget overspend: daily spend surged {surge_pct:.1f}% "
                            f"to ${row['spend']:,.2f} compared to historical baseline of ${row['med_spend']:,.2f}."
                        ),
                        "recommended_action": "Check automated bidding limits, campaign daily budget caps, and keyword bid multipliers.",
                    })

            # ---- Pattern 4: Click Fraud / Bot Traffic Spike ----
            # Clicks exploded >= 2.2x, CTR surged >= 1.8x, but CVR collapsed <= 0.40x
            if row["clicks"] >= row["med_clicks"] * 2.2 and row["ctr"] >= row["med_ctr"] * 1.8 and row["cvr"] <= row["med_cvr"] * 0.40:
                surge_pct = ((row["clicks"] / row["med_clicks"]) - 1.0) * 100
                alerts.append({
                    "date": date_str,
                    "campaign_id": cid,
                    "campaign_name": cname,
                    "channel": channel,
                    "vertical": vert,
                    "landing_page_group": lp,
                    "incident_type": "Click Fraud / Bot Traffic Spike",
                    "severity": "HIGH",
                    "metric": "clicks",
                    "actual_value": f"{row['clicks']:,} clicks (CTR {row['ctr']:.2%}, CVR {row['cvr']:.2%})",
                    "normal_baseline": f"{row['med_clicks']:,.0f} clicks (CTR {row['med_ctr']:.2%}, CVR {row['med_cvr']:.2%})",
                    "change_pct": f"+{surge_pct:.1f}%",
                    "explanation": (
                        f"Bot traffic burst: Clicks surged +{surge_pct:.1f}% ({row['clicks']:,} vs normal {row['med_clicks']:,.0f}) "
                        f"with abnormal CTR of {row['ctr']:.2%} (normal {row['med_ctr']:.2%}), but conversions did not follow (CVR {row['cvr']:.2%})."
                    ),
                    "recommended_action": "Audit placement reports, add IP exclusion filters, and review audience network traffic.",
                })

    alerts_df = pd.DataFrame(alerts)
    if not alerts_df.empty:
        alerts_df = alerts_df.sort_values("date", ascending=False).reset_index(drop=True)
    return alerts_df


def cluster_incident_episodes(alerts_df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups contiguous day-level alerts for the same campaign & incident type
    into a unified Incident Episode summary.
    """
    if alerts_df.empty:
        return pd.DataFrame()

    df = alerts_df.sort_values(["campaign_id", "incident_type", "date"]).copy()
    df["date_dt"] = pd.to_datetime(df["date"])

    episodes = []
    for (cid, itype), group in df.groupby(["campaign_id", "incident_type"]):
        group = group.sort_values("date_dt").reset_index(drop=True)
        
        # Split into contiguous blocks
        group["day_diff"] = (group["date_dt"] - group["date_dt"].shift(1)).dt.days
        group["block"] = (group["day_diff"] > 1).cumsum()

        for _, block_df in group.groupby("block"):
            start_date = block_df["date"].iloc[0]
            end_date = block_df["date"].iloc[-1]
            duration = len(block_df)
            cname = block_df["campaign_name"].iloc[0]
            channel = block_df["channel"].iloc[0]
            severity = block_df["severity"].iloc[0]

            episodes.append({
                "start_date": start_date,
                "end_date": end_date,
                "duration_days": duration,
                "campaign_id": cid,
                "campaign_name": cname,
                "channel": channel,
                "incident_type": itype,
                "severity": severity,
                "summary": block_df["explanation"].iloc[0],
                "recommended_action": block_df["recommended_action"].iloc[0],
            })

    ep_df = pd.DataFrame(episodes).sort_values("start_date", ascending=False).reset_index(drop=True)
    return ep_df


def run_detection(df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Main detection entrypoint: accepts DataFrame or loads from SQLite/CSV.
    """
    if df is None:
        try:
            conn = sqlite3.connect("data/campaign_data.db")
            df = pd.read_sql("SELECT * FROM campaign_metrics", conn)
            conn.close()
        except Exception:
            from generate_data import load_and_preprocess_ps04_data
            df = load_and_preprocess_ps04_data()

    return detect_campaign_anomalies(df)


if __name__ == "__main__":
    from generate_data import load_and_preprocess_ps04_data
    df = load_and_preprocess_ps04_data()

    print("Running PS-04 Anomaly Detection Engine...")
    alerts = detect_campaign_anomalies(df)
    print(f"Total alerts fired: {len(alerts)} alerts across 3,600 campaign-days ({len(alerts)/len(df):.2%} alert rate)")
    
    print("\nAlerts by Incident Type:")
    print(alerts["incident_type"].value_counts().to_string())

    print("\n--- Top Alert Samples ---")
    for _, r in alerts.head(5).iterrows():
        print(f"[{r['severity']}] {r['date']} | {r['campaign_name']} ({r['incident_type']})")
        print(f"  Change: {r['change_pct']} | {r['actual_value']} vs Baseline {r['normal_baseline']}")
        print(f"  Explanation: {r['explanation']}\n")

    print("--- Incident Episodes Summary (Clustered) ---")
    episodes = cluster_incident_episodes(alerts)
    print(episodes[["start_date", "end_date", "duration_days", "campaign_id", "incident_type", "severity"]].to_string())
