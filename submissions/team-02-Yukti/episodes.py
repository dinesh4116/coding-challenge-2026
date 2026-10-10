"""Group flagged days into incident episodes and decide what to notify.

An episode is a run of flagged days (Alert or Human Review) for one campaign
and metric, in one direction, with at most `max_gap_days` quiet days inside.
Within an episode only the first day notifies; later days are suppressed unless
severity rises above anything already notified, or the route upgrades from
Human Review to Alert (escalation). A direction change or a longer gap starts
a new episode, so distinct incidents are not merged.
"""
from __future__ import annotations

import pandas as pd

from src.detector_config import DetectorConfig
from src.scoring import ALERT, REVIEW, SEVERITY_RANK

ROUTE_RANK = {REVIEW: 1, ALERT: 2}


def assign_episodes(df: pd.DataFrame, cfg: DetectorConfig | None = None):
    """Return (records with episode_id/notification, episode summary)."""
    cfg = cfg or DetectorConfig()
    df = df.copy()
    df["episode_id"] = pd.NA
    df["notification"] = ""
    flagged = df[df["route"].isin([ALERT, REVIEW])].sort_values(["campaign_id", "metric", "date"])

    counter = 0
    for (cid, metric), g in flagged.groupby(["campaign_id", "metric"], sort=True):
        last_date = last_dir = None
        max_sev = max_route = 0
        for idx, r in g.iterrows():
            gap = None if last_date is None else (r["date"] - last_date).days - 1
            if last_date is None or gap > cfg.max_gap_days or r["direction"] != last_dir:
                counter += 1
                ep_id = f"EP{counter:04d}"
                max_sev, max_route = SEVERITY_RANK[r["severity"]], ROUTE_RANK[r["route"]]
                note = "new"
            else:
                sev, rte = SEVERITY_RANK[r["severity"]], ROUTE_RANK[r["route"]]
                if sev > max_sev or rte > max_route:
                    note = "escalation"
                    max_sev, max_route = max(sev, max_sev), max(rte, max_route)
                else:
                    note = "suppressed"
            df.at[idx, "episode_id"] = ep_id
            df.at[idx, "notification"] = note
            last_date, last_dir = r["date"], r["direction"]

    return df, summarize_episodes(df)


def summarize_episodes(df: pd.DataFrame) -> pd.DataFrame:
    ep = df[df["episode_id"].notna()]
    cols = ["episode_id", "campaign_id", "metric", "direction", "start_date", "end_date",
            "flagged_days", "peak_severity", "peak_abs_z", "max_evidence", "top_route",
            "notifications", "suppressed"]
    if ep.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for eid, g in ep.groupby("episode_id", sort=True):
        rows.append({
            "episode_id": eid, "campaign_id": g["campaign_id"].iloc[0],
            "metric": g["metric"].iloc[0], "direction": g["direction"].iloc[0],
            "start_date": g["date"].min(), "end_date": g["date"].max(),
            "flagged_days": len(g),
            "peak_severity": max(g["severity"], key=SEVERITY_RANK.get),
            "peak_abs_z": round(float(g["z"].abs().max()), 2),
            "max_evidence": float(g["evidence_score"].max()),
            "top_route": ALERT if (g["route"] == ALERT).any() else REVIEW,
            "notifications": int(g["notification"].isin(["new", "escalation"]).sum()),
            "suppressed": int((g["notification"] == "suppressed").sum()),
        })
    return pd.DataFrame(rows)[cols]
