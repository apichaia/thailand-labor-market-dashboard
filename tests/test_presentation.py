"""How numbers are presented: correlation wording, the map legend, tied province ranks and trend windows.
Uses small made-up frames only (no network, no downloaded data)."""
import numpy as np
import pandas as pd

from analytics.selectors import Filters
from dashboard import charts, overview


def _quarters(values, start=2560 * 4):
    return pd.DataFrame({"period_idx": range(start, start + len(values)), "v": values})


def test_delta_text_has_the_change_and_never_a_flag():
    df = _quarters([10.0] * 20 + [12.0])
    txt = overview._delta_text(df, "v", df.iloc[-1], "pct", 1)
    assert "+20.0%" in txt and "ผิดปกติ" not in txt
    assert overview._delta_text(_quarters([1.0, 2.0]), "v", _quarters([1.0, 2.0]).iloc[-1], "pt", 2) == "ไม่มีข้อมูลปีก่อน"


def test_correlation_wording_matches_size():
    assert overview.corr_phrase(-0.28) == "สัมพันธ์เชิงลบระดับอ่อน"
    assert overview.corr_phrase(0.05) == "แทบไม่สัมพันธ์กัน"
    assert overview.corr_phrase(0.4) == "สัมพันธ์เชิงบวกระดับปานกลาง"
    assert overview.corr_phrase(-0.8) == "สัมพันธ์เชิงลบระดับสูง"


def test_legend_lists_highest_first_in_region_colours():
    df = pd.DataFrame({"region": ["ภาคเหนือ", "ภาคใต้", "ภาคกลาง"], "value": [1.0, 3.0, float("nan")]})
    html = charts.region_map_legend(df, "อัตรา", "%", vertical=True)
    assert html.index("ภาคใต้") < html.index("ภาคเหนือ") < html.index("ภาคกลาง")
    assert charts.REGION_COLORS["ภาคใต้"] in html and charts.NO_VALUE_COLOR in html and "ไม่มีข้อมูล" in html


def test_province_ranks_share_rank_and_keep_ties_at_the_cut():
    df = pd.DataFrame({"province": list("ABCDEFG"), "r": [2.5, 2.5, 2.3, 2.1, 2.1, 2.1, 1.0]})
    d = charts.province_ranks(df, "r", top=5)
    assert list(d["province"]) == list("ABCDEF")   # F ties with 5th place, so it is kept
    assert list(d["rank"]) == [1, 1, 3, 4, 4, 4]
    assert list(d["tied"]) == [True, True, False, True, True, True]


def test_trend_window_reaches_back_seven_years_and_marks_focus():
    f = Filters(year_min=2569, year_max=2569)
    t = f.for_trend()
    assert (t.year_min, t.year_max) == (2563, 2569)
    assert f.focus == (2569 * 4, 2569 * 4 + 3)
    wide = Filters(year_min=2555, year_max=2569)
    assert wide.for_trend().year_min == 2555


def test_shade_focus_draws_only_when_the_pick_is_part_of_the_chart():
    import plotly.graph_objects as go

    fig = go.Figure()
    charts.shade_focus(fig, 100, 119, (116, 119))
    assert len(fig.layout.shapes) == 1 and fig.layout.shapes[0].x0 == 15.5
    fig2 = go.Figure()
    charts.shade_focus(fig2, 100, 119, (100, 119))
    assert len(fig2.layout.shapes) == 0


def test_compare_helpers_use_only_valid_values():
    import numpy as np
    from dashboard import overview

    rs = pd.DataFrame({"period_idx": [10277, 10277, 10276], "region": ["ภาคใต้", "ภาคเหนือ", "ภาคใต้"], "wage": [np.nan, 15000.0, 12000.0]})
    g = overview.region_gap(rs, "ภาคเหนือ", "ภาคใต้", "wage", 10277)
    assert g["a"] == (15000.0, 10277) and g["b"] == (12000.0, 10276)       # the south uses its own newest valid quarter, and says which
    assert abs(g["gap"] - 25.0) < 1e-9
    assert overview.region_gap(rs, "ภาคเหนือ", "ภาคกลาง", "wage", 10277) is None
    emp = pd.DataFrame({"period_idx": [1, 2], "emp_pct": [60.0, 61.5]})
    un = pd.DataFrame({"period_idx": [1], "rate_pct": [1.0]})
    rows = {r["name"]: r for r in overview.period_rows(emp, un, None, 1, 2)}
    assert abs(rows["อัตรามีงานทำ (%)"]["diff"] - 1.5) < 1e-9
    assert rows["อัตราการว่างงาน (%)"]["diff"] is None and rows["ค่าจ้างเฉลี่ย (บาท)"]["v1"] is None


def test_region_rank_lists_highest_first_and_dims_unselected():
    d = pd.DataFrame({"region": ["ภาคใต้", "ภาคเหนือ", "ภาคกลาง"], "rate_pct": [0.5, 1.2, float("nan")]})
    html = overview.region_rank_html(d, "rate_pct", "%", 2, ["ภาคเหนือ"])
    assert html.index("ภาคเหนือ") < html.index("ภาคใต้") and "ภาคกลาง" not in html      # no value: not ranked
    assert "1.20%" in html and "0.50%" in html and 'class="rk dim"' in html and 'width:100.0%' in html


def test_restrict_from_drops_only_earlier_quarters_and_keeps_attrs():
    from data_processing.pipeline import DataBundle, restrict_from

    b = DataBundle()
    t = pd.DataFrame({"period_idx": [2562 * 4, 2563 * 4, 2563 * 4 + 1], "v": [1.0, 2.0, 3.0]})
    t.attrs["scope"] = "ทั่วประเทศ"
    b.tables["x"] = t
    b.tables["geo_like"] = pd.DataFrame({"name": ["a"]})
    b.excluded["x"] = [2562 * 4, 2563 * 4 + 1]
    r = restrict_from(b, 2563)
    assert r.tables["x"]["v"].tolist() == [2.0, 3.0] and r.tables["x"].attrs["scope"] == "ทั่วประเทศ"
    assert len(r.tables["geo_like"]) == 1 and r.excluded["x"] == [2563 * 4 + 1]
    assert len(b.tables["x"]) == 3        # the original is untouched


def test_conflict_table_names_each_table_and_its_value():
    from dashboard import components as ui

    rows = [{"period_idx": 2567 * 4, "values": {"ตารางเพศ×อายุ OS_02_0016_03": 66.97, "ตารางภาค×เพศ LFS_02_20540": 6.7}, "gap": 60.27, "unit": "%",
             "gap_unit": "จุด", "reason": "ตาราง สสช. 3 ตารางให้อัตรามีงานทำระดับประเทศต่างกันเกิน 0.05 จุด"}]
    html = ui.conflict_table_html(rows, lambda i: "ไตรมาส 1/2567")
    assert "ไตรมาส 1/2567" in html and "66.97%" in html and "6.70%" in html and "OS_02_0016_03" in html and "60.27 จุด" in html


def test_shade_excluded_merges_neighbouring_quarters_into_one_band():
    import plotly.graph_objects as go

    fig = go.Figure()
    charts.shade_excluded(fig, 100, 120, [105, 106, 107, 110, 999])      # 999 is outside the chart
    assert len(fig.layout.shapes) == 2
    assert (fig.layout.shapes[0].x0, fig.layout.shapes[0].x1) == (4.5, 7.5)
