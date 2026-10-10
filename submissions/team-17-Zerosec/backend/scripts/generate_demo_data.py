"""Generate the SYNTHETIC demo dataset (data/demo_campaigns.csv).

This is NOT the official hackathon data. It imitates the problem statement:
20 campaigns x 180 days with a few seeded situations (broken conversion tag,
budget exhausted, bid strategy change, a spend spike, and a portfolio-wide
seasonal shift that is NOT an incident). Label columns let us measure
precision/recall. Run:  python -m scripts.generate_demo_data
"""
from pathlib import Path

import numpy as np
import pandas as pd

START = "2026-01-01"
DAYS = 180
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "demo_campaigns.csv"

# Fixed sizes for the campaigns that carry incidents (so the incidents are
# measurable) and for three deliberately tiny campaigns (1-3 conversions/day).
FIXED_IMPRESSIONS = {"C01": 2_000_000, "C03": 500_000, "C05": 300_000, "C09": 150_000,
                     "C12": 200_000, "C18": 3_000, "C19": 4_000, "C20": 3_500}
TINY = {"C18", "C19", "C20"}
CHANNELS = ["search", "social", "display", "video"]

# (incident_type, campaign or None for all, effect window, label window, is_incident)
SITUATIONS = [
    ("tracking_break", "C05", ("2026-02-20", "2026-02-26"), ("2026-02-20", "2026-02-26"), 1),
    ("budget_exhausted", "C12", ("2026-03-19", "2026-03-31"), ("2026-03-19", "2026-03-31"), 1),
    ("bid_strategy_change", "C03", ("2026-04-15", "2026-06-29"), ("2026-04-15", "2026-04-21"), 1),
    ("spend_spike", "C09", ("2026-05-08", "2026-05-09"), ("2026-05-08", "2026-05-09"), 1),
    ("seasonal_shift", None, ("2026-05-20", "2026-06-02"), ("2026-05-20", "2026-06-02"), 0),
]


def _in(day: pd.Timestamp, window: tuple[str, str]) -> bool:
    return pd.Timestamp(window[0]) <= day <= pd.Timestamp(window[1])


def _effects(campaign: str, day: pd.Timestamp) -> dict:
    """Multipliers applied on this campaign-day by the seeded situations."""
    fx = {"imp": 1.0, "click": 1.0, "conv": 1.0, "cpc": 1.0, "tracked": 1.0}
    for kind, target, effect, _, _ in SITUATIONS:
        if (target is None or target == campaign) and _in(day, effect):
            if kind == "tracking_break":
                fx["tracked"] = 0.05          # clicks unchanged, conversions not recorded
            elif kind == "budget_exhausted":
                fx["imp"] *= 0.02             # delivery stops -> everything collapses
            elif kind == "bid_strategy_change":
                fx["cpc"] *= 1.6
                fx["click"] *= 0.9
                fx["conv"] *= 0.95 / 0.9      # net conversions x0.95
            elif kind == "spend_spike":
                fx["cpc"] *= 2.5
            elif kind == "seasonal_shift":
                fx["imp"] *= 1.4              # volumes up 40%, ratios unchanged
    return fx


def generate(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(START, periods=DAYS, freq="D")
    rows = []
    for i in range(1, 21):
        cid = f"C{i:02d}"
        base = FIXED_IMPRESSIONS.get(cid, float(np.exp(rng.uniform(np.log(2_000), np.log(2_000_000)))))
        ctr = 0.02 if cid in TINY else rng.uniform(0.005, 0.04)
        cvr = 0.03 if cid in TINY else rng.uniform(0.01, 0.08)
        cpc = rng.uniform(0.3, 3.0)
        aov = rng.uniform(20, 150)
        channel = CHANNELS[i % len(CHANNELS)]
        for day in dates:
            fx = _effects(cid, day)
            weekday = 0.85 if day.dayofweek >= 5 else 1.0
            impressions = int(round(base * weekday * rng.lognormal(0, 0.08) * fx["imp"]))
            clicks = int(rng.poisson(impressions * ctr * fx["click"]))
            true_conv = int(rng.poisson(clicks * cvr * fx["conv"]))
            conversions = int(rng.binomial(true_conv, fx["tracked"])) if fx["tracked"] < 1 else true_conv
            spend = round(clicks * cpc * fx["cpc"] * rng.lognormal(0, 0.05), 2)
            revenue = round(conversions * aov * rng.lognormal(0, 0.10), 2)
            rows.append({"date": day, "campaign_id": cid, "campaign_name": f"Campaign {i:02d} ({channel})",
                         "channel": channel, "impressions": impressions, "clicks": clicks, "spend": spend,
                         "conversions": conversions, "revenue": revenue, "is_incident": 0, "incident_type": ""})
    df = pd.DataFrame(rows)
    for kind, target, _, label, is_incident in SITUATIONS:
        mask = df["date"].between(pd.Timestamp(label[0]), pd.Timestamp(label[1]))
        if target is not None:
            mask &= df["campaign_id"] == target
        df.loc[mask, "is_incident"] = is_incident
        df.loc[mask, "incident_type"] = kind
    return df


def main() -> None:
    df = generate(42)
    out = df.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(out)} SYNTHETIC rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
