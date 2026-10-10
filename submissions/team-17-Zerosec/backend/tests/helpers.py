import numpy as np
import pandas as pd

RAW = ["impressions", "clicks", "spend", "conversions", "revenue"]


def make_campaign_df(campaign_id="C1", days=60, start="2026-01-01", seed=0, impressions=10000,
                     clicks=300, spend=300.0, conversions=18, revenue=900.0) -> pd.DataFrame:
    """A synthetic stable campaign in the loader's frame format (Poisson counts, lognormal money)."""
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "campaign_id": campaign_id,
        "date": pd.date_range(start, periods=days, freq="D"),
        "impressions": rng.poisson(impressions, days).astype(float),
        "clicks": rng.poisson(clicks, days).astype(float),
        "spend": spend * rng.lognormal(0, 0.05, days),
        "conversions": rng.poisson(conversions, days).astype(float),
        "revenue": revenue * rng.lognormal(0, 0.05, days),
        "row_present": True,
    })
