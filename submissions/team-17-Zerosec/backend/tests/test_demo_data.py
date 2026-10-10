from scripts.generate_demo_data import generate


def test_shape_and_dates():
    df = generate(42)
    assert len(df) == 3600 and df["campaign_id"].nunique() == 20
    assert str(df["date"].min())[:10] == "2026-01-01" and str(df["date"].max())[:10] == "2026-06-29"


def test_deterministic():
    assert generate(42).equals(generate(42))


def test_labels():
    df = generate(42)
    types = set(df["incident_type"]) - {""}
    assert types == {"tracking_break", "budget_exhausted", "bid_strategy_change", "spend_spike", "seasonal_shift"}
    assert (df.loc[df.incident_type == "seasonal_shift", "is_incident"] == 0).all()
    assert (df.loc[df.incident_type.isin(types - {"seasonal_shift"}), "is_incident"] == 1).all()


def test_tracking_break_keeps_clicks():
    df = generate(42)
    c = df[df.campaign_id == "C05"].set_index("date")
    window = c.loc["2026-02-20":"2026-02-26"]
    before = c.loc["2026-01-23":"2026-02-19"]
    assert window.conversions.median() < 0.2 * before.conversions.median()
    assert 0.8 < window.clicks.median() / before.clicks.median() < 1.2


def test_has_low_volume_campaigns():
    df = generate(42)
    assert (df.groupby("campaign_id").conversions.median() <= 3).sum() >= 3
