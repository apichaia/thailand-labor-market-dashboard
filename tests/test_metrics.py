import math

import numpy as np
import pandas as pd
import pytest

from analytics import metrics as m
from data_processing import validation as v


def _series(vals, start=10000):
    return pd.DataFrame({"period_idx": range(start, start + len(vals)), "v": vals})


def test_percentage_change():
    assert m.pct_change(110, 100) == pytest.approx(10.0)
    assert m.pct_change(90, 100) == pytest.approx(-10.0)


def test_percentage_change_missing_or_zero_base_is_nan_not_zero():
    assert math.isnan(m.pct_change(5, 0))
    assert math.isnan(m.pct_change(5, None))
    assert math.isnan(m.pct_change(None, 5))


def test_yoy_uses_exact_four_quarter_lag():
    d = m.add_changes(_series([100, 101, 102, 103, 110, 111]), "v")
    last = d.iloc[-1]
    assert last["yoy_pct"] == pytest.approx((111 - 101) / 101 * 100)
    assert last["qoq_pct"] == pytest.approx((111 - 110) / 110 * 100)
    assert math.isnan(d.iloc[2]["yoy_pct"])  # no prior-year quarter


def test_yoy_nan_when_comparison_quarter_missing():
    d = _series([100, 101, 102, 103, 110, 111])
    d = d[d["period_idx"] != 10001]
    out = m.add_changes(d, "v")
    assert math.isnan(out[out["period_idx"] == 10005]["yoy_pct"].iloc[0])


def test_qoq_and_yoy_are_distinct_columns():
    d = m.add_changes(_series([100, 120, 90, 95, 130]), "v")
    assert {"qoq_pct", "yoy_pct"} <= set(d.columns)
    assert d.iloc[-1]["qoq_pct"] != d.iloc[-1]["yoy_pct"]


def test_kpi_snapshot_reports_reason_when_not_comparable():
    s = _series([100.0, 102.0])
    k = m.kpi_snapshot(s, "v", 10001)
    assert k["qoq_abs"] == pytest.approx(2.0)
    assert math.isnan(k["yoy_pct"]) and k["yoy_reason"]


def test_unemployment_rate_with_valid_denominator():
    assert m.unemployment_rate(400.0, 40000.0) == pytest.approx(1.0)


def test_unemployment_rate_invalid_denominator_is_nan():
    assert math.isnan(m.unemployment_rate(400.0, 0))
    assert math.isnan(m.unemployment_rate(400.0, None))
    out = m.unemployment_rate(pd.Series([1.0, 2.0]), pd.Series([100.0, np.nan]))
    assert out.iloc[0] == pytest.approx(1.0) and math.isnan(out.iloc[1])


def test_sum_by_period_refuses_total_rows():
    d = pd.DataFrame({"p": [1, 1, 1], "sex": ["รวม", "ชาย", "หญิง"], "x": [30, 10, 20]})
    with pytest.raises(ValueError):
        m.sum_by_period(d, "x", ["p"], total_cols=["sex"])


def test_total_equals_sum_of_partition():
    d = pd.DataFrame({"p": [1, 1, 2, 2], "sex": ["ชาย", "หญิง", "ชาย", "หญิง"], "x": [10.0, 20.0, 5.0, 5.0]})
    out = m.sum_by_period(d, "x", ["p"], total_cols=["sex"])
    assert out["x"].tolist() == [30.0, 10.0]


def test_significant_change_detection_needs_enough_data():
    d = pd.DataFrame({"yoy_pct": [1.0, 2.0, 3.0]})
    assert not m.detect_significant_changes(d)["significant"].any()


def test_significant_change_flags_outlier():
    vals = [1.0, -1.0, 0.5, -0.5, 0.8, -0.8, 0.2, -0.2, 0.3, -0.3, 40.0]
    out = m.detect_significant_changes(pd.DataFrame({"yoy_pct": vals}))
    assert out["significant"].tolist()[-1] and out["significant"].sum() == 1


def _econ(n=12, start=10000):
    return pd.DataFrame({"period_idx": range(start, start + n), "rate_pct": np.linspace(1, 2, n), "year_be": 2560, "quarter": 1})


def test_join_economic_matching_keys_inner_only():
    un = _econ(12)
    gdp = pd.DataFrame({"period_idx": range(10004, 10016), "gdp_yoy_pct": np.arange(12.0)})
    merged, rep = m.merge_economic_indicators(un, gdp)
    assert rep.ok and len(merged) == 8
    assert merged["period_idx"].min() == 10004


def test_join_rejects_duplicate_keys_no_double_counting():
    un = _econ(4)
    gdp = pd.DataFrame({"period_idx": [10000, 10000], "gdp_yoy_pct": [1.0, 2.0]})
    merged, rep = m.merge_economic_indicators(un, gdp)
    assert merged.empty and not rep.ok


def test_join_rejects_non_overlapping_periods():
    merged, rep = m.merge_economic_indicators(_econ(4), pd.DataFrame({"period_idx": [1, 2], "gdp_yoy_pct": [1.0, 2.0]}))
    assert merged.empty and not rep.ok


def test_join_rejects_empty_input():
    merged, rep = m.merge_economic_indicators(pd.DataFrame(), _econ(4))
    assert merged.empty and not rep.ok


def test_frequency_mismatch_blocks_join():
    assert v.check_frequency_compat("quarterly", "annual", "t")


def test_correlation_insufficient_data():
    out = m.correlation_summary(pd.Series([1, 2, 3]), pd.Series([3, 2, 1]))
    assert math.isnan(out["pearson"]) and out["reason"]


def test_correlation_perfect_negative():
    x = pd.Series(range(20), dtype=float)
    out = m.correlation_summary(x, -x)
    assert out["pearson"] == pytest.approx(-1.0) and out["n"] == 20
