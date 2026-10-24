"""Tests for the regional map pipeline. All data below is a TEST FIXTURE (invented), never shown in the app."""
import json

import numpy as np
import pandas as pd

from analytics import selectors as sel
from data_processing import clean
from data_processing.pipeline import DataBundle
from data_processing.province_codes import NAME_ALIASES, PROVINCE_CODES

NAMES = list(PROVINCE_CODES.values())


def _raw(year=2568, region_of=lambda i: "ภาคเหนือ" if i % 2 else "ภาคใต้", names=None, extra=None):
    names = names or NAMES
    rows = [{"YEAR": year, "QUARTER": "ไตรมาส 1", "REGION": region_of(i), "PROVINCE": n} for i, n in enumerate(names)]
    return pd.DataFrame(rows + (extra or []))


def test_province_codes_are_complete_and_unique():
    assert len(PROVINCE_CODES) == 77 and len(set(PROVINCE_CODES.values())) == 77


def test_province_region_keeps_complete_year():
    df, rep = clean.clean_province_region(_raw())
    assert rep.ok and df["province"].nunique() == 77 and set(df["iso"]) == set(PROVINCE_CODES)


def test_province_region_spelling_variant_and_trailing_space_normalised():
    names = list(NAMES)
    names[names.index("สุราษฎร์ธานี")] = "สุราษฏร์ธานี"          # variant spelling used by NSO
    names[names.index("นครราชสีมา")] = "นครราชสีมา "            # trailing space
    df, rep = clean.clean_province_region(_raw(names=names))
    assert rep.ok and df["province"].nunique() == 77
    assert NAME_ALIASES["สุราษฏร์ธานี"] == "สุราษฎร์ธานี"


def test_province_region_conflicting_regions_rejected():
    dup = [{"YEAR": 2568, "QUARTER": "ไตรมาส 1", "REGION": "ภาคกลาง", "PROVINCE": NAMES[0]}]
    df, rep = clean.clean_province_region(_raw(extra=dup))
    assert df.empty and any(i.check == "double_counting" for i in rep.errors)


def test_province_region_unknown_province_rejected():
    df, rep = clean.clean_province_region(_raw(extra=[{"YEAR": 2568, "QUARTER": "ไตรมาส 1", "REGION": "ภาคกลาง", "PROVINCE": "จังหวัดสมมติ"}]))
    assert df.empty and any(i.check == "label_mapping" for i in rep.errors)


def test_province_region_incomplete_year_excluded_not_filled():
    two_years = pd.concat([_raw(2567), _raw(2568, names=NAMES[:70])])
    df, rep = clean.clean_province_region(two_years)
    assert set(df["year_be"]) == {2567} and any(i.check == "coverage" for i in rep.warnings)


def _square(x):  # tiny closed ring, counter-clockwise
    return [[x, 0], [x + 1, 0], [x + 1, 1], [x, 1], [x, 0]]


def _geo(codes, ring=_square):
    feats = [{"type": "Feature", "properties": {"shapeISO": c}, "geometry": {"type": "Polygon", "coordinates": [ring(i)]}}
             for i, c in enumerate(codes)]
    return {"type": "FeatureCollection", "features": feats}


def _write(tmp_path, gj):
    p = tmp_path / "g.geojson"
    p.write_text(json.dumps(gj), encoding="utf-8")
    return p


def test_geo_valid_file_and_orientation_normalised(tmp_path):
    geo, rep = clean.clean_geo(_write(tmp_path, _geo(list(PROVINCE_CODES))))
    assert rep.ok and len(geo["features"]) == 77
    ring = geo["features"][0]["geometry"]["coordinates"][0]
    assert clean._ring_area([tuple(p) for p in ring]) < 0  # exterior clockwise (what Plotly needs)


def test_geo_missing_province_rejected(tmp_path):
    geo, rep = clean.clean_geo(_write(tmp_path, _geo(list(PROVINCE_CODES)[:-1])))
    assert len(geo) == 0 and any(i.check == "join" for i in rep.errors)


def test_geo_duplicate_code_rejected(tmp_path):
    codes = list(PROVINCE_CODES)
    codes[1] = codes[0]
    geo, rep = clean.clean_geo(_write(tmp_path, _geo(codes)))
    assert len(geo) == 0 and any(i.check == "duplicates" for i in rep.errors)


def test_geo_not_geojson_rejected(tmp_path):
    p = tmp_path / "x.geojson"
    p.write_text("<html>blocked</html>", encoding="utf-8")
    geo, rep = clean.clean_geo(p)
    assert len(geo) == 0 and not rep.ok


def _bundle(year=2568):
    idx = year * 4
    pr, _ = clean.clean_province_region(_raw(year, region_of=lambda i: "ภาคเหนือ" if i % 2 else "ภาคใต้"))
    reg = pd.DataFrame({"period_idx": [idx, idx], "region": ["ภาคเหนือ", "ภาคใต้"], "u_k": [10.0, 20.0], "rate_pct": [1.0, np.nan],
                        "year_be": year, "quarter": 1})
    b = DataBundle()
    b.tables = {"province_region": pr, "region_series": reg}
    b.geo = {"type": "FeatureCollection", "features": []}
    return b, idx


def test_map_frame_assigns_region_value_to_every_province():
    b, idx = _bundle()
    out = sel.region_map_frame(b, sel.Filters(2555, 2569), idx, "u_k")
    assert len(out.data) == 77 and set(out.data["value"]) == {10.0, 20.0}


def test_map_frame_missing_rate_stays_empty_not_zero():
    b, idx = _bundle()
    d = sel.region_map_frame(b, sel.Filters(2555, 2569), idx, "rate_pct").data
    assert d.loc[d["region"] == "ภาคใต้", "value"].isna().all()


def test_map_frame_respects_region_filter():
    b, idx = _bundle()
    d = sel.region_map_frame(b, sel.Filters(2555, 2569, regions=("ภาคเหนือ",)), idx, "u_k").data
    assert d.loc[d["region"] == "ภาคใต้", "value"].isna().all() and d.loc[d["region"] == "ภาคเหนือ", "value"].eq(10.0).all()


def test_map_frame_year_without_definition_is_unavailable():
    b, _ = _bundle()
    out = sel.region_map_frame(b, sel.Filters(2555, 2569), 2560 * 4, "u_k")
    assert out.empty and "2560" in out.unavailable_reason


def test_map_frame_without_geometry_is_unavailable():
    b, idx = _bundle()
    b.geo = None
    assert sel.region_map_frame(b, sel.Filters(2555, 2569), idx, "u_k").empty


# ---- map figure: one distinct colour per region (TEST FIXTURE data) ----
def _frame(values):
    regions = list(values)
    iso = list(PROVINCE_CODES)[: len(regions)]
    return pd.DataFrame({"iso": iso, "province": NAMES[: len(regions)], "region": regions, "value": [values[r] for r in regions]})


def test_region_map_one_trace_and_distinct_colour_per_region():
    from dashboard import charts

    vals = {r: float(i + 1) for i, r in enumerate(charts.REGION_COLORS)}
    fig = charts.region_map({"type": "FeatureCollection", "features": []}, _frame(vals), "อัตรา", "%")
    assert len(fig.data) == 5
    colours = [t.colorscale[0][1] for t in fig.data]
    assert len(set(colours)) == 5 and charts.NO_VALUE_COLOR not in colours


def test_region_map_region_without_value_is_grey_and_listed_as_no_data():
    from dashboard import charts

    df = _frame({"ภาคเหนือ": 1.0, "ภาคใต้": float("nan")})
    fig = charts.region_map({"type": "FeatureCollection", "features": []}, df, "อัตรา", "%")
    by_name = {t.name: t.colorscale[0][1] for t in fig.data}
    assert by_name["ภาคใต้"] == charts.NO_VALUE_COLOR and by_name["ภาคเหนือ"] == charts.REGION_COLORS["ภาคเหนือ"]
    legend = charts.region_map_legend(df, "อัตรา", "%")
    assert "ไม่มีข้อมูล" in legend and "1.00 %" in legend


def test_region_map_returns_none_when_nothing_to_draw():
    from dashboard import charts

    assert charts.region_map({"type": "FeatureCollection", "features": []}, _frame({"ภาคเหนือ": float("nan")}), "อัตรา", "%") is None
