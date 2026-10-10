import pandas as pd
from models import campaign, metric, alert
from .anomaly_detector import detect

REQUIRED = ["campaign_id", "campaign_name", "date", "spend", "impressions", "clicks", "conversions"]
OPTIONAL_NUM = ["revenue", "budget"]
OPTIONAL_TXT = ["channel", "vertical", "landing_page_group"]
NUMERIC = REQUIRED[3:] + OPTIONAL_NUM

def load_df(src):
    df = pd.read_csv(src)
    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))
    for c in OPTIONAL_NUM:
        if c not in df.columns:
            df[c] = 0
    for c in OPTIONAL_TXT:
        if c not in df.columns:
            df[c] = None
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    for c in NUMERIC:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).clip(lower=0)
    df = df.dropna(subset=["date", "campaign_id"])
    return df.drop_duplicates(["campaign_id", "date"], keep="last")

def analyze(cid):
    rows = metric.series(cid)
    if not rows:
        return 0
    alerts = detect(pd.DataFrame(rows))
    alert.clear_open(cid)
    for a in alerts:
        a["campaign_id"] = cid
    if alerts:
        alert.save_many(alerts)
    return len(alerts)

def process(src):
    df = load_df(src)
    total_alerts = 0
    for ext_id, g in df.groupby("campaign_id"):
        cid = campaign.upsert(str(ext_id), str(g["campaign_name"].iloc[0]), *[g[c].iloc[0] for c in OPTIONAL_TXT])
        metric.upsert_many([(cid, r.date, r.spend, int(r.impressions), int(r.clicks),
                             int(r.conversions), r.revenue, r.budget) for r in g.itertuples()])
        total_alerts += analyze(cid)
    return {"campaigns": int(df["campaign_id"].nunique()), "rows": len(df), "alerts": total_alerts}
