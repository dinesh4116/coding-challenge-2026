import pandas as pd
import pytest

from app.services.detector import Anomaly
from app.services.diagnosis import diagnose, format_value


def A(metric, obs, exp, score, direction):
    return Anomaly(campaign_id="C1", date=pd.Timestamp("2026-02-20"), metric=metric, observed=obs,
                   expected=exp, lower=exp * 0.8, upper=exp * 1.2, score=score,
                   pct_change=(obs - exp) / exp, direction=direction, severity="high", history_points=28)


TRACKING = ([A("conversions", 2, 18, -8.0, "down")],
            {"conversions": {"observed": 2, "expected": 18, "score": -8.0},
             "clicks": {"observed": 300, "expected": 310, "score": -0.3}})
DELIVERY = ([A("spend", 5, 300, -20, "down"), A("impressions", 200, 10000, -30, "down")],
            {"spend": {"observed": 5, "expected": 300, "score": -20},
             "impressions": {"observed": 200, "expected": 10000, "score": -30}})
COST = ([A("spend", 450, 300, 6, "up"), A("cpc", 1.6, 1.0, 7, "up")], {})
SPIKE = ([A("spend", 900, 300, 12, "up")], {})
VOLUME = ([A("impressions", 20000, 10000, 9, "up")], {})
ALL_TYPE_CASES = [TRACKING, DELIVERY, COST, SPIKE, VOLUME]


def test_tracking_issue_explanation_uses_measured_values():
    d = diagnose(*TRACKING)
    assert d.alert_type == "tracking_issue"
    assert d.explanation.startswith("Conversions fell to 2, compared with a baseline of 18")
    assert "Clicks stayed within their normal range" in d.explanation
    assert d.diagnostic_steps[0].startswith("Verify the conversion tag")


def test_delivery_drop():
    d = diagnose(*DELIVERY)
    assert d.alert_type == "delivery_drop" and "budget" in d.diagnostic_steps[0]


def test_cost_shift_beats_spend_spike():
    assert diagnose(*COST).alert_type == "cost_efficiency_shift"


def test_spend_spike():
    assert diagnose(*SPIKE).alert_type == "spend_spike"


def test_conversion_drop_with_clicks_also_down_is_not_tracking():
    d = diagnose([A("conversions", 2, 18, -8, "down")],
                 {"clicks": {"observed": 30, "expected": 300, "score": -9}})
    assert d.alert_type != "tracking_issue"


@pytest.mark.parametrize("case", ALL_TYPE_CASES)
def test_language_is_hedged(case):
    text = diagnose(*case).explanation.lower()
    assert "may" in text and "confirmed" not in text and "caused by" not in text


def test_format_value():
    assert format_value("conversions", 1234) == "1,234" and format_value("cvr", 0.021) == "2.10%"
    assert format_value("roas", 3.2) == "3.20x" and format_value("spend", 12.5) == "12.50"
