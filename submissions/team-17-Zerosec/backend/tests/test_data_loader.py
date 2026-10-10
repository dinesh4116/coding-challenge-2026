import pytest
import pandas as pd

from app.services.data_loader import DataValidationError, load_csv_bytes


def load(text: str, max_rows: int = 1000):
    return load_csv_bytes(text.encode(), max_rows)


def test_aliases_mapped():
    r = load("Campaign,Day,Cost,Conv.,Clicks\nA,2026-01-01,10,1,5\n")
    assert r.metrics == ["clicks", "spend", "conversions"]
    assert {"campaign_id", "date"} <= set(r.frame.columns)


def test_formatted_numbers():
    r = load('campaign_id,date,spend,impressions\nA,2026-01-01,"$1,234.50","1,200"\n')
    assert r.frame.spend[0] == 1234.5 and r.frame.impressions[0] == 1200


def test_bom_and_semicolon():
    r = load_csv_bytes(b"\xef\xbb\xbfdate;campaign_id;spend\n2026-01-01;A;10\n", 1000)
    assert r.frame.spend[0] == 10


def test_leading_zero_ids_preserved():
    r = load("campaign_id,date,spend\n007,2026-01-01,1\n7,2026-01-01,2\n")
    assert sorted(r.frame.campaign_id.unique()) == ["007", "7"]


def test_invalid_dates_dropped_with_warning():
    r = load("campaign_id,date,spend\nA,2026-01-01,1\nA,not-a-date,2\nA,2026-01-02,3\n")
    assert r.valid_rows == 2 and any("1 row(s) dropped" in w for w in r.warnings)


def test_non_numeric_and_negative_become_missing():
    r = load("campaign_id,date,spend\nA,2026-01-01,abc\nA,2026-01-02,-5\nA,2026-01-03,4\n")
    assert r.frame.spend.isna().sum() == 2
    assert any("non-numeric" in w for w in r.warnings) and any("negative" in w for w in r.warnings)


def test_duplicates_dropped_or_summed():
    r = load("campaign_id,date,spend\nA,2026-01-01,1\nA,2026-01-01,1\nA,2026-01-02,2\nA,2026-01-02,3\n")
    assert list(r.frame.spend) == [1.0, 5.0] and len(r.warnings) == 2


def test_missing_days_filled():
    r = load("campaign_id,date,spend\nA,2026-01-01,1\nA,2026-01-04,1\n")
    assert len(r.frame) == 4 and r.frame.row_present.sum() == 2
    assert any("2 missing day(s)" in w for w in r.warnings)


def test_missing_required_columns():
    with pytest.raises(DataValidationError, match="campaign"):
        load("date,spend\n2026-01-01,1\n")
    with pytest.raises(DataValidationError, match="metric"):
        load("campaign_id,date,foo\nA,2026-01-01,1\n")


@pytest.mark.parametrize("text", ["", "campaign_id,date,spend\n", "campaign_id,date,spend\nA,bad,1\n"])
def test_no_valid_records(text):
    with pytest.raises(DataValidationError, match="no valid records|Could not parse"):
        load(text)


def test_row_limit():
    with pytest.raises(DataValidationError, match="limit"):
        load("campaign_id,date,spend\n" + "A,2026-01-01,1\n" * 3, max_rows=2)


def test_label_column_detected_and_not_a_metric():
    r = load("campaign_id,date,spend,is_anomaly\nA,2026-01-01,1,1\n")
    assert r.has_labels and r.frame.is_incident[0] == 1 and "is_incident" not in r.metrics


# ---- final-review fixes ------------------------------------------------------
def test_decimal_comma_with_semicolon_delimiter():
    r = load("campaign_id;date;spend;revenue\nA;2026-01-01;12,5;1.234,50\n")
    assert r.frame.spend[0] == 12.5 and r.frame.revenue[0] == 1234.5
    assert any("decimal comma" in w for w in r.warnings)


def test_day_first_dates():
    rows = "".join(f"A,{d:02d}/01/2026,1\n" for d in range(1, 20))
    r = load("campaign_id,date,spend\n" + rows)
    assert len(r.frame) == 19 and r.frame.date.min() == pd.Timestamp("2026-01-01")


def test_campaign_id_column_wins_over_campaign_name():
    r = load("Campaign,Campaign ID,Day,Cost\nBrand,1,2026-01-01,5\nBrand,2,2026-01-01,7\n")
    assert sorted(r.frame.campaign_id) == ["1", "2"] and set(r.frame.campaign_name) == {"Brand"}


def test_infinite_values_are_missing():
    r = load("campaign_id,date,clicks\nA,2026-01-01,inf\nA,2026-01-02,5\n")
    assert r.frame.clicks.isna().sum() == 1 and any("non-numeric" in w for w in r.warnings)


def test_mixed_timezones_do_not_crash():
    r = load("campaign_id,date,spend\nA,2026-01-01T00:00:00+00:00,1\nA,2026-01-02T00:00:00+05:00,2\n")
    assert r.valid_rows == 2
