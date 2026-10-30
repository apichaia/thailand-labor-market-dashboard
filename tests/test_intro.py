"""The intro film: its numbers come only from the validated tables, and the composition follows the HyperFrames contract."""
import pandas as pd

from dashboard import intro
from data_processing import intro_payload
from data_processing.pipeline import DataBundle


def _bundle():
    b = DataBundle()
    b.tables["national"] = pd.DataFrame({"period_idx": [10275, 10276, 10277], "rate_pct": [0.9, None, 0.95]})
    b.tables["lm_national"] = pd.DataFrame({"period_idx": [10275, 10276, 10277], "emp_pct": [69.0, 69.2, None], "wage": [15000.0, None, None]})
    b.tables["lm_employed_national"] = pd.DataFrame({"period_idx": [10275, 10276], "emp_k": [41000.0, 41190.0]})
    return b


def test_each_indicator_uses_its_own_latest_valid_quarter():
    k = {x["key"]: x for x in intro_payload.build(_bundle())["kpis"]}
    assert k["emp"]["value"] == 69.2 and k["emp"]["period"] == "ไตรมาส 1/2569"
    assert k["unemp"]["value"] == 0.95 and k["unemp"]["period"] == "ไตรมาส 2/2569"
    assert k["wage"]["value"] == 15000.0 and k["wage"]["period"] == "ไตรมาส 4/2568"      # a gap is not filled: the older valid quarter is named
    assert abs(k["emp_n"]["value"] - 41.19) < 1e-9 and k["emp_n"]["unit"] == "ล้านคน"


def test_missing_tables_leave_the_pieces_out():
    p = intro_payload.build(DataBundle())
    assert p["kpis"] == [] and p["map"] is None


def test_composition_follows_the_hyperframes_contract():
    page = intro.standalone_html({"kpis": [{"key": "emp", "label": "อัตราการมีงานทำ", "value": 69.5, "dec": 2, "unit": "%", "period": "ไตรมาส 2/2569"}], "map": None})
    for needle in ('data-composition-id="main"', 'data-start="0"', 'data-width="1920"', 'data-height="1080"', "window.__timelines", "paused: true"):
        assert needle in page
    assert "Math.random" not in page and "Date.now" not in page      # deterministic: the film renders identically every time
    assert 'id="root"' not in page                                   # Streamlit owns #root: the overlay must not reuse it
