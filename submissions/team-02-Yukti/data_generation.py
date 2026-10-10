"""Deterministic synthetic advertising benchmark for Adomaly.

Daily metrics are generated from latent per-campaign rates (CPM, CTR, CVR) so
that impressions, clicks and conversions stay mutually consistent. Incidents
are applied to the latent rates/spend before counts are sampled (except
tracking failure, which thins *recorded* conversions). Ground-truth labels are
written to a separate file and are never part of the metrics table.

Run:  python -m src.data_generation
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src import config as C

# Size tiers drive base spend; small campaigns are naturally noisier.
TIERS = {"small": (40, 120), "medium": (300, 900), "large": (2500, 8000)}
TIER_OF = {i: ("small" if i <= 5 else "medium" if i <= 10 else "large") for i in range(1, 16)}

# Fixed, documented incident schedule (day index 0..179). Dev incidents fall in
# days 28-89, eval incidents in days 90-179; none cross the split boundary.
INCIDENTS = [
    # campaign, type, start_day, end_day, affected_metric, magnitude, severity
    ("C03", "spend_spike", 40, 41, "spend", 2.8, "high"),
    ("C08", "tracking_failure", 55, 60, "conversions", 0.05, "high"),
    ("C12", "ctr_collapse", 65, 68, "ctr", 0.45, "medium"),
    ("C14", "gradual_degradation", 50, 75, "conversion_rate", 0.55, "medium"),
    ("C01", "spend_spike", 120, 121, "spend", 3.0, "high"),
    ("C13", "spend_spike", 150, 150, "spend", 1.6, "medium"),
    ("C05", "tracking_failure", 100, 104, "conversions", 0.0, "high"),
    ("C11", "tracking_failure", 140, 146, "conversions", 0.4, "medium"),
    ("C07", "ctr_collapse", 110, 114, "ctr", 0.4, "high"),
    ("C15", "ctr_collapse", 160, 163, "ctr", 0.7, "low"),
    ("C09", "gradual_degradation", 125, 150, "conversion_rate", 0.5, "medium"),
    ("C02", "gradual_degradation", 135, 165, "conversion_rate", 0.6, "low"),
]
# magnitude meaning: spend_spike = spend multiplier; tracking_failure = share of
# conversions still recorded; ctr_collapse = CTR multiplier;
# gradual_degradation = CVR multiplier reached linearly by end_day.

# Non-incident sustained shifts (planned budget increase / seasonal demand).
# A good detector should NOT keep alerting on these.
BENIGN = [
    ("C06", "seasonal_budget_increase", 70, "spend", 1.40),
    ("C10", "seasonal_budget_increase", 130, "spend", 1.35),
]
BENIGN_RAMP_DAYS = 5


def _campaign_profiles(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for i in range(1, C.N_CAMPAIGNS + 1):
        tier = TIER_OF[i]
        lo, hi = TIERS[tier]
        rows.append({
            "campaign_id": f"C{i:02d}",
            "tier": tier,
            "base_spend": float(np.exp(rng.uniform(np.log(lo), np.log(hi)))),
            "cpm": rng.uniform(4.0, 12.0),
            "ctr": rng.uniform(0.006, 0.03),
            "cvr": rng.uniform(0.02, 0.08),
            "spend_sigma": rng.uniform(0.06, 0.14),
            "weekend_factor": rng.uniform(0.70, 1.15),
            "trend": rng.uniform(-0.10, 0.10),  # total drift over 180 days
        })
    return pd.DataFrame(rows)


def _incident_modifiers(cid: str, n: int):
    spend_m, ctr_m, cvr_m, retain = (np.ones(n) for _ in range(4))
    for c, typ, s, e, _, mag, _ in INCIDENTS:
        if c != cid:
            continue
        if typ == "spend_spike":
            spend_m[s:e + 1] *= mag
        elif typ == "ctr_collapse":
            ctr_m[s:e + 1] *= mag
        elif typ == "tracking_failure":
            retain[s:e + 1] = mag
        elif typ == "gradual_degradation":
            cvr_m[s:e + 1] *= np.linspace(1.0, mag, e - s + 1)
    for c, _, s, _, mag in BENIGN:
        if c == cid:
            ramp = np.ones(n)
            ramp[s:] = mag
            ramp[s:s + BENIGN_RAMP_DAYS] = np.linspace(1.0, mag, BENIGN_RAMP_DAYS + 1)[1:]
            spend_m *= ramp
    return spend_m, ctr_m, cvr_m, retain


def generate_dataset(seed: int = C.SEED):
    """Return (metrics, labels, benign_events) DataFrames. Pure function of seed."""
    rng = np.random.default_rng(seed)
    profiles = _campaign_profiles(rng)
    dates = pd.date_range(C.START_DATE, periods=C.N_DAYS, freq="D")
    n = C.N_DAYS
    is_weekend = np.asarray(dates.dayofweek >= 5)
    t = np.arange(n) / (n - 1)

    frames = []
    for p in profiles.itertuples():
        spend_m, ctr_m, cvr_m, retain = _incident_modifiers(p.campaign_id, n)
        weekday = np.where(is_weekend, p.weekend_factor, 1.0)
        spend = (p.base_spend * weekday * (1 + p.trend * t)
                 * rng.lognormal(0, p.spend_sigma, n) * spend_m)
        cpm = p.cpm * rng.lognormal(0, 0.05, n)
        ctr = np.clip(p.ctr * np.where(is_weekend, 0.95, 1.0)
                      * rng.lognormal(0, 0.06, n) * ctr_m, 0, 1)
        cvr = np.clip(p.cvr * rng.lognormal(0, 0.08, n) * cvr_m, 0, 1)

        impressions = rng.poisson(spend / cpm * 1000)
        clicks = rng.binomial(impressions, ctr)
        true_conv = rng.binomial(clicks, cvr)
        conversions = rng.binomial(true_conv, retain)  # tracking loss

        frames.append(pd.DataFrame({
            "date": dates, "campaign_id": p.campaign_id,
            "spend": np.round(spend, 2), "impressions": impressions.astype(int),
            "clicks": clicks.astype(int), "conversions": conversions.astype(int),
        }))
    metrics = pd.concat(frames, ignore_index=True)[C.METRIC_COLUMNS]

    labels = pd.DataFrame([{
        "incident_id": f"INC{k:03d}", "campaign_id": c, "incident_type": typ,
        "start_date": dates[s].date().isoformat(), "end_date": dates[e].date().isoformat(),
        "affected_metric": m, "severity": sev, "magnitude": mag,
        "period": "dev" if dates[e] <= C.DEV_END else "eval",
    } for k, (c, typ, s, e, m, mag, sev) in enumerate(INCIDENTS, start=1)])[C.LABEL_COLUMNS]

    benign = pd.DataFrame([{
        "event_id": f"BEN{k:03d}", "campaign_id": c, "event_type": typ,
        "start_date": dates[s].date().isoformat(), "affected_metric": m, "magnitude": mag,
        "period": "dev" if dates[s] <= C.DEV_END else "eval",
    } for k, (c, typ, s, m, mag) in enumerate(BENIGN, start=1)])

    return metrics, labels, benign


def save_dataset(metrics, labels, benign) -> None:
    C.RAW_DIR.mkdir(parents=True, exist_ok=True)
    metrics.assign(date=metrics["date"].dt.strftime("%Y-%m-%d")).to_csv(C.METRICS_FILE, index=False)
    labels.to_csv(C.LABELS_FILE, index=False)
    benign.to_csv(C.BENIGN_FILE, index=False)


def main() -> None:
    metrics, labels, benign = generate_dataset()
    save_dataset(metrics, labels, benign)
    print(f"Wrote {len(metrics)} metric rows -> {C.METRICS_FILE.relative_to(C.ROOT)}")
    print(f"Wrote {len(labels)} incidents -> {C.LABELS_FILE.relative_to(C.ROOT)}")
    print(f"Wrote {len(benign)} benign events -> {C.BENIGN_FILE.relative_to(C.ROOT)}")


if __name__ == "__main__":
    main()
