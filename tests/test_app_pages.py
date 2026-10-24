"""Smoke test: every page and sub-tab of the real app renders without an exception (uses the downloaded data)."""
from pathlib import Path

import pytest

import config

APP = Path(__file__).resolve().parents[1] / "app.py"
SUB = {
    "ภูมิภาค": ("nav_region", ["การว่างงานรายภาค", "ค่าจ้างและการมีงานทำรายภาค"]),
    "กลุ่มแรงงาน": ("nav_pop", ["การศึกษา", "เพศ", "กลุ่มอายุ", "จำนวนผู้มีงานทำ"]),
}
OVERVIEW_SELECTS = {
    "ov_map_metric": ["อัตรามีงานทำ (%)", "อัตราการว่างงาน (%)", "ค่าจ้างเฉลี่ย (บาท)"],
    "ov_trend_choice": ["อัตรามีงานทำ", "อัตราการว่างงาน", "ค่าจ้างเฉลี่ย", "จำนวนผู้ว่างงาน"],
}


def _w(at, kind, key):
    return [w for w in getattr(at, kind) if w.key == key][0]


@pytest.mark.skipif(not (config.DATA_RAW / "nso_u_region.csv").exists(), reason="needs the downloaded raw data")
def test_every_page_and_sub_tab_renders():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=300).run()
    assert not at.exception, [e.value for e in at.exception]
    assert _w(at, "radio", "nav_page").options == ["ภาพรวม", "ภูมิภาค", "กลุ่มแรงงาน"]
    for key, options in OVERVIEW_SELECTS.items():
        for opt in options:
            _w(at, "selectbox", key).set_value(opt).run()
            assert not at.exception, (key, opt, [e.value for e in at.exception])
    for page in ["ภาพรวม", "ภูมิภาค", "กลุ่มแรงงาน"]:
        _w(at, "radio", "nav_page").set_value(page).run()
        assert not at.exception, (page, [e.value for e in at.exception])
        if page in SUB:
            key, tabs = SUB[page]
            for tab in tabs:
                _w(at, "radio", key).set_value(tab).run()
                assert not at.exception, (page, tab, [e.value for e in at.exception])


FILTER_COMBOS = [
    {"f_year": "ทุกปี"}, {"f_year": 2567, "f_quarters": [2, 3]}, {"f_year": 2566, "f_regions": ["ภาคเหนือ"]},
    {"f_year": 2565, "f_sex": "หญิง"}, {"f_year": 2566, "f_regions": ["ภาคใต้"], "f_sex": "ชาย"},
    {"f_year": 2566, "f_edus": ["ประถมศึกษา"]},
]


@pytest.mark.skipif(not (config.DATA_RAW / "nso_u_region.csv").exists(), reason="needs the downloaded raw data")
def test_every_page_renders_under_each_filter_combination():
    from streamlit.testing.v1 import AppTest

    for combo in FILTER_COMBOS:
        at = AppTest.from_file(str(APP), default_timeout=300)
        for k, v in combo.items():
            at.session_state[k] = v
        at.run()
        for page in ["ภาพรวม", "ภูมิภาค", "กลุ่มแรงงาน"]:
            _w(at, "radio", "nav_page").set_value(page).run()
            assert not at.exception, (combo, page, [e.value for e in at.exception])
            for key, tabs in ([SUB[page]] if page in SUB else []):
                for tab in tabs:
                    _w(at, "radio", key).set_value(tab).run()
                    assert not at.exception, (combo, page, tab, [e.value for e in at.exception])
