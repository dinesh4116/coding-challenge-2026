import numpy as np
import pandas as pd

from app.services.features import add_derived_metrics


def frame(**cols):
    n = len(next(iter(cols.values())))
    return pd.DataFrame({"campaign_id": "A", "date": pd.date_range("2026-01-01", periods=n), **cols})


def test_ratios_computed():
    f, added = add_derived_metrics(
        frame(impressions=[1000.], clicks=[50.], spend=[100.], conversions=[5.], revenue=[400.]),
        ["impressions", "clicks", "spend", "conversions", "revenue"])
    assert added == ["ctr", "cvr", "cpc", "cpa", "roas"]
    assert f.ctr[0] == 0.05 and f.cvr[0] == 0.1 and f.cpc[0] == 2.0 and f.cpa[0] == 20.0 and f.roas[0] == 4.0


def test_zero_and_small_denominators_are_nan_not_inf():
    f, _ = add_derived_metrics(frame(impressions=[0., 100.], clicks=[0., 5.]), ["impressions", "clicks"])
    assert f.ctr.isna().all() and not np.isinf(f.select_dtypes("number")).any().any()


def test_only_available_inputs():
    _, added = add_derived_metrics(frame(clicks=[50.], spend=[10.]), ["clicks", "spend"])
    assert added == ["cpc"]
