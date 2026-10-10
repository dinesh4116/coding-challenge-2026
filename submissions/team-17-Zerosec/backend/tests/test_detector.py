import numpy as np
import pandas as pd

from app.services.detector import DetectorConfig, classify_severity, detect
from app.services.features import add_derived_metrics
from tests.helpers import RAW, make_campaign_df

cfg = DetectorConfig()


def anoms(df, metric):
    return [a for a in detect(df, RAW, cfg).anomalies if a.metric == metric]


def test_stable_campaign_has_no_anomalies():
    assert detect(make_campaign_df(days=60), RAW, cfg).anomalies == []


def test_conversion_drop_with_stable_clicks():
    df = make_campaign_df(days=60)
    df.loc[50, "conversions"] = 2
    [a] = anoms(df, "conversions")
    assert a.direction == "down" and 14 <= a.expected <= 22 and a.severity in ("high", "critical")
    assert not [x for x in anoms(df, "clicks") if x.date == df.date[50]]


def test_spend_spike():
    df = make_campaign_df(days=60)
    df.loc[50, "spend"] *= 3
    assert [a.direction for a in anoms(df, "spend")] == ["up"]


def test_spend_drop_is_critical():
    df = make_campaign_df(days=60)
    df.loc[50, "spend"] *= 0.1
    [a] = anoms(df, "spend")
    assert a.direction == "down" and a.severity == "critical"


def test_insufficient_history_not_scored():
    df = make_campaign_df(days=20)
    df.loc[5, "spend"] *= 5  # only 5 prior days
    res = detect(df, RAW, cfg)
    assert not [a for a in res.anomalies if a.date <= df.date[13]]
    assert res.scores[res.scores.date <= df.date[13]].expected.isna().all()


def test_low_volume_single_conversion_swing_is_quiet_but_large_10pct_drift_alerts():
    small = make_campaign_df(days=60, conversions=2)
    small.loc[50, "conversions"] = 0
    assert anoms(small, "conversions") == []
    large = make_campaign_df(days=60, conversions=2000, seed=1)
    large.loc[50, "conversions"] = 1800
    assert [a.direction for a in anoms(large, "conversions")] == ["down"]


def test_constant_history_zero_mad():
    df = make_campaign_df(days=40)
    df["spend"] = 100.0
    df.loc[39, "spend"] = 130.0
    res = detect(df, ["spend"], cfg)
    assert [a.date for a in res.anomalies] == [df.date[39]]
    assert np.isfinite(res.scores.score.dropna()).all()


def test_no_future_leakage():
    df = make_campaign_df(days=60)
    before = detect(df, RAW, cfg).scores
    df.loc[55, "spend"] *= 10
    after = detect(df, RAW, cfg).scores

    def early(s):
        return s[s.date < df.date[55]].reset_index(drop=True)

    pd.testing.assert_frame_equal(early(before), early(after))


def test_missing_days_skipped():
    df = make_campaign_df(days=60)
    df.loc[40:42, RAW] = np.nan
    df.loc[40:42, "row_present"] = False
    res = detect(df, RAW, cfg)
    assert res.anomalies == [] and res.scores[res.scores.date == df.date[45]].expected.notna().all()


def test_zero_day_is_safe_and_flagged():
    df = make_campaign_df(days=60)
    df.loc[50, RAW] = 0
    f, derived = add_derived_metrics(df, RAW)
    res = detect(f, RAW + derived, cfg)
    assert {"spend", "impressions", "clicks"} <= {a.metric for a in res.anomalies}
    assert np.isfinite(res.scores.select_dtypes("number").fillna(0)).all().all()


def test_severity_thresholds():
    assert classify_severity(4.0, -0.2, "spend", cfg) == "medium"
    assert classify_severity(7.0, -0.2, "spend", cfg) == "high"
    assert classify_severity(-4.0, -0.95, "spend", cfg) == "critical"
    assert classify_severity(-4.0, -0.95, "cvr", cfg) == "medium"


def test_mad_metrics_false_positive_rate_is_low_on_stable_series():
    # 60 stable 90-day campaigns; money metrics have 5% lognormal noise.
    flagged = scored = 0
    for seed in range(60):
        res = detect(make_campaign_df(days=90, seed=seed), ["spend", "revenue"], cfg)
        flagged += len(res.anomalies)
        scored += int(res.scores.expected.notna().sum())
    assert flagged / scored < 0.001


def test_large_volume_drop_is_high_but_large_rise_needs_a_strong_score():
    assert classify_severity(-4.0, -0.6, "conversions", cfg) == "high"
    assert classify_severity(4.0, 0.8, "conversions", cfg) == "medium"


def test_displayed_band_matches_flag_for_mad_metrics():
    df = make_campaign_df(days=150, seed=3)
    days = list(range(30, 150, 4))  # sweep spikes of +6% .. +45% so some land near the threshold
    df.loc[days, "spend"] *= np.linspace(1.06, 1.45, len(days))
    s = detect(df, ["spend"], cfg).scores
    s = s[s.expected.notna() & (s["pct_change"].abs() >= cfg.min_pct_change)]
    outside = (s.observed > s.upper + 1e-6) | (s.observed < s.lower - 1e-6)
    assert (outside == s.is_anomaly).all()


def test_sustained_outage_keeps_alerting():
    df = make_campaign_df(days=90)
    df.loc[50:64, "spend"] *= 0.02  # 15-day delivery outage
    flagged = {a.date for a in anoms(df, "spend")}
    assert set(df.date[50:65]) <= flagged


def test_permanent_level_shift_becomes_the_new_normal():
    df = make_campaign_df(days=120)
    df.loc[40:, "spend"] *= 1.6
    flagged = [a.date for a in anoms(df, "spend")]
    assert df.date[40] in flagged and max(flagged) < df.date[90]


def test_absurd_count_value_is_fast_and_finite():
    import time
    from app.services.detector import poisson_z
    t = time.time()
    z = poisson_z(200_000_000, 100.0)
    assert time.time() - t < 0.5 and np.isfinite(z) and z > 10
