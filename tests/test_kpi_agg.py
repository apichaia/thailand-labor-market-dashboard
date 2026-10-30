"""The summary cards: weighted rates (never an average of percentages), the plain wage mean, and which quarters count."""
import pandas as pd
import pytest

from analytics.selectors import Filters
from dashboard import kpi_agg as k


def test_selected_quarters_follow_years_and_ticked_quarters_and_stop_at_the_latest():
    latest = 2569 * 4 + 1                                           # ไตรมาส 2/2569
    allq = k.selected_quarters(Filters(2563, 2569), latest)
    assert allq[0] == 2563 * 4 and allq[-1] == latest and len(allq) == 26
    q1 = k.selected_quarters(Filters(2563, 2569, quarters=(1,)), latest)
    assert q1 == [y * 4 for y in range(2563, 2570)]                  # only Q1 of each year
    assert k.selected_quarters(Filters(2569, 2569), latest) == [2569 * 4, 2569 * 4 + 1]   # no future quarters
    assert k.selected_quarters(Filters(2569, 2569, quarters=(4,)), latest) == []
    assert k.selected_quarters(Filters(2560, 2562), latest) == []    # nothing before 2563


def test_unemployment_rate_is_sum_over_sum_not_the_mean_of_percentages():
    u = {1: 10.0, 2: 90.0}
    lf = {1: 1000.0, 2: 3000.0}                                      # rates 1% and 3%
    a = k.unemployment_rate(u, lf, {1: 1.0, 2: 3.0}, [1, 2])
    assert a.value == pytest.approx(100 / 4000 * 100) and a.value != pytest.approx(2.0)
    only2 = k.unemployment_rate(u, lf, {2: 3.0}, [1, 2])             # quarter 1's rate failed a check: it is left out of both sums
    assert only2.value == pytest.approx(3.0) and only2.used == [2]


def test_employment_rate_uses_the_population_behind_each_published_rate():
    emp = {1: 30.0, 2: 40.0}                                         # million employed
    rate = {1: 60.0, 2: 80.0}                                        # populations 50 and 50
    a = k.employment_rate(emp, rate, [1, 2])
    assert a.value == pytest.approx(70 / 100 * 100) and a.value == pytest.approx(70.0)
    assert k.employment_rate(emp, {}, [1, 2]).value is None          # no published rate: no summary, with the reason on the card
    assert "ไม่เพียงพอ" in k.employment_rate(emp, {}, [1, 2]).reason


def test_simple_mean_skips_quarters_without_a_value_and_never_uses_zero():
    a = k.simple_mean({1: 15000.0, 3: 16000.0}, [1, 2, 3, 4])
    assert a.value == 15500.0 and a.used == [1, 3]
    assert k.simple_mean({}, [1, 2]).value is None


def test_to_dict_keeps_one_value_per_quarter_and_drops_gaps():
    df = pd.DataFrame({"period_idx": [5, 5, 6, 7], "v": [1.0, 9.0, None, 3.0]})
    assert k.to_dict(df, "v") == {5: 1.0, 7: 3.0}


def test_span_text_says_how_many_selected_quarters_were_used():
    f = Filters(2563, 2569)
    qs = list(range(2563 * 4, 2563 * 4 + 6))
    assert k.span_text(qs, qs, f) == "พ.ศ. 2563–2564 · ใช้ข้อมูล 6 ไตรมาส"
    assert k.span_text(qs, qs[:4], f).endswith("ใช้ได้ 4 จาก 6 ไตรมาสที่เลือก")
    assert "เฉพาะไตรมาส 1" in k.span_text([2563 * 4, 2564 * 4], [2563 * 4], Filters(2563, 2564, quarters=(1,)))


def test_region_unemployment_is_weighted_and_skips_excluded_quarters():
    import pandas as pd
    from dashboard import kpi_agg

    rs = pd.DataFrame({"region": ["ก"] * 3 + ["ข"] * 2, "period_idx": [1, 2, 3, 1, 2],
                       "u_k": [10.0, 20.0, 99.0, 5.0, None], "lf_k": [1000.0, 3000.0, 100.0, 500.0, 500.0]})
    r = kpi_agg.region_unemployment(rs, [1, 2, 3], excluded=[3]).set_index("region")
    assert abs(r.loc["ก", "rate_pct"] - 30 / 4000 * 100) < 1e-9 and r.loc["ก", "n_used"] == 2     # sum / sum, quarter 3 left out
    assert abs(r.loc["ข", "rate_pct"] - 1.0) < 1e-9 and r.loc["ข", "used"] == [1]                  # a quarter without a numerator is not a zero
    assert kpi_agg.region_unemployment(rs, [9]).empty
