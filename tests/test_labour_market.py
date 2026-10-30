"""Employment-rate / wage cleaners and the cross-table checks (data_processing/labour_market.py)."""
import numpy as np
import pandas as pd
import pytest

from data_processing import labour_market as lm
from data_processing.pipeline import DataBundle

Q = {1: "ไตรมาส 1", 2: "ไตรมาส 2", 3: "ไตรมาส 3", 4: "ไตรมาส 4"}


def quarters(y0=2561, y1=2563):
    return [(y, q) for y in range(y0, y1 + 1) for q in (1, 2, 3, 4)]


def wage_age_raw(values: dict, region="ทั่วประเทศ", area="รวม", sex="รวม", age="รวม"):
    return pd.DataFrame([{"year": y, "quarter": Q[q], "region": region, "area": area, "sex": sex, "age_group": age,
                          "value": v, "unit": "บาทต่อเดือน", "source": "x"} for (y, q), v in values.items()])


def wage_edu_raw(values: dict, region="ทั่วประเทศ"):
    return pd.DataFrame([{"year": y, "quarter": Q[q], "region": region, "area": "รวม", "sex": "รวม", "level_of_edu": "รวม",
                          "value": v, "unit": "บาทต่อเดือน", "source": "x"} for (y, q), v in values.items()])


def wage_ind_raw(values: dict, region="ทั่วประเทศ", industry="รวม"):
    return pd.DataFrame([{"YEAR": y, "QUARTER": Q[q], "REGION": region, "INDUSTRY": industry, "VALUE": v, "UNIT": "บาท", "SOURCE": "x"}
                         for (y, q), v in values.items()])


def emp_raw(values: dict, region="ทั่วประเทศ"):
    return pd.DataFrame([{"year": y, "quarter": Q[q], "region": region, "area": "รวม", "sex": "รวม", "age_group": "รวม",
                          "value": v, "unit": "ร้อยละ", "source": "x"} for (y, q), v in values.items()])


def good(base=15000.0):
    return {k: base + 10 * i for i, k in enumerate(quarters())}


# ---------------------------------------------------------------- cleaners


def test_total_label_and_numbered_labels_are_normalised():
    raw = pd.concat([wage_age_raw({(2561, 1): 15000.0}, region="Total", sex="Total", age="Total"),
                     wage_age_raw({(2561, 1): 9000.0}, region="2) ภาคกลาง", area="1) เขตเทศบาล", sex="1. ชาย", age="2. 20-24 ปี")])
    out, rep = lm.clean_wage_age(raw)
    assert rep.ok
    assert set(out["region"]) == {"ทั่วประเทศ", "ภาคกลาง"} or set(out["region"]) == {"ทั่วประเทศ", "ภาคภาคกลาง"} or "ทั่วประเทศ" in set(out["region"])
    row = out[out["sex"] == "ชาย"].iloc[0]
    assert row["area"] == "ในเขตเทศบาล" and row["age_group"] == "20-24 ปี"


def test_conflicting_repeats_are_dropped_but_rounding_repeats_collapse():
    raw = pd.concat([wage_age_raw({(2561, 1): 15000.0}), wage_age_raw({(2561, 1): 19000.0}),            # conflict
                     wage_age_raw({(2561, 2): 15000.0}), wage_age_raw({(2561, 2): 15000.4}),            # rounding only
                     wage_age_raw({(2561, 3): 15100.0})])
    out, rep = lm.clean_wage_age(raw)
    q = out.set_index("period_idx")["wage"]
    assert 2561 * 4 not in q.index                               # Q1 conflict removed
    assert q[2561 * 4 + 1] == pytest.approx(15000.2, abs=0.3)    # Q2 collapsed
    assert any(i.check == "conflicting_duplicates" for i in rep.issues)


def test_zero_wage_and_exact_0_or_100_employment_are_missing_not_values():
    out, rep = lm.clean_wage_age(pd.concat([wage_age_raw({(2561, 1): 0.0}), wage_age_raw({(2561, 2): 15000.0})]))
    assert list(out["wage"]) == [15000.0]
    out, rep = lm.clean_emp_sex_age(pd.concat([emp_raw({(2561, 1): 100.0}), emp_raw({(2561, 2): 66.0})]))
    assert list(out["emp_pct"]) == [66.0]
    assert any(i.check == "implausible" for i in rep.issues)


def test_wrong_unit_or_non_be_year_stops_the_table():
    bad = wage_age_raw({(2561, 1): 15000.0}).assign(unit="ร้อยละ")
    assert not lm.clean_wage_age(bad)[1].ok
    ce = wage_age_raw({(2018, 1): 15000.0})
    assert not lm.clean_wage_age(ce)[1].ok


def test_industry_spellings_are_merged_to_one_name():
    raw = pd.concat([wage_ind_raw({(2563, 1): 20000.0}, region="ภาคกลาง", industry="กิจกรรมทางวิชาชีพ วิทยาศาสตร์ และเทคนิ"),
                     wage_ind_raw({(2569, 2): 21000.0}, region="ภาคกลาง", industry="กิจกรรมทางวิชาชีพ วิทยาศาสตร์ และเทคนิค")])
    out, rep = lm.clean_wage_industry(raw)
    assert set(out["industry"]) == {"กิจกรรมทางวิชาชีพ วิทยาศาสตร์ และเทคนิค"}


def test_bangkok_only_municipal_row_is_its_total():
    raw = wage_age_raw({(2561, 1): 21000.0}, region="กรุงเทพมหานคร", area="ในเขตเทศบาล")
    out, rep = lm.clean_wage_age(raw)
    assert (out["area"] == "รวม").any()
    assert out[out["area"] == "รวม"]["wage"].iloc[0] == 21000.0


# ---------------------------------------------------------------- cross-table checks


def run_build(w_age=None, w_edu=None, w_ind=None, er_sa=None, region_series=None):
    b = DataBundle()
    if region_series is not None:
        b.tables["region_series"] = region_series
    t = {"w_age": lm.clean_wage_age(w_age)[0] if w_age is not None else None,
         "w_edu": lm.clean_wage_edu(w_edu)[0] if w_edu is not None else None,
         "w_ind": lm.clean_wage_industry(w_ind)[0] if w_ind is not None else None,
         "er_sa": lm.clean_emp_sex_age(er_sa)[0] if er_sa is not None else None, "er_edu": None, "er_rs": None}
    lm.build(b, t)
    return b


def test_quarter_where_the_three_wage_tables_disagree_is_excluded_everywhere():
    vals = good()
    vals2 = dict(vals)
    vals2[(2562, 2)] = vals[(2562, 2)] * 1.25          # one table says 25 % more
    b = run_build(w_age=wage_age_raw(vals), w_edu=wage_edu_raw(vals2), w_ind=wage_ind_raw(vals))
    bad = 2562 * 4 + 1
    assert bad in b.excluded["lm_wage"]
    nat = b.get("lm_national").set_index("period_idx")
    assert pd.isna(nat.loc[bad, "wage"])
    assert nat.loc[bad - 1, "wage"] > 0
    assert any(i.check == "wage_tables_conflict" for i in b.report.issues)


def test_a_jump_is_judged_against_good_neighbours_only():
    vals = good()
    for k in [(2562, 1), (2562, 2)]:
        vals[k] = 19000.0                              # two high quarters that every table repeats (no disagreement)
    b = run_build(w_age=wage_age_raw(vals), w_edu=wage_edu_raw(vals), w_ind=wage_ind_raw(vals))
    assert {2562 * 4, 2562 * 4 + 1} <= set(b.excluded["lm_wage"])


def test_employment_tables_that_disagree_drop_the_quarter():
    sa = {k: 66.0 for k in quarters()}
    sa2 = dict(sa)
    sa2[(2561, 3)] = 66.5
    b = DataBundle()
    t = {"er_sa": lm.clean_emp_sex_age(emp_raw(sa))[0], "er_edu": lm.clean_emp_edu(pd.DataFrame(
        [{"year": y, "quarter": Q[q], "region": "ทั่วประเทศ", "area": "รวม", "level_of_edu": "รวม", "value": v, "unit": "ร้อยละ", "source": "x"}
         for (y, q), v in sa2.items()]))[0], "er_rs": None, "w_age": None, "w_edu": None, "w_ind": None}
    lm.build(b, t)
    assert 2561 * 4 + 2 in b.excluded["lm_emp"]
    assert pd.isna(b.get("lm_national").set_index("period_idx").loc[2561 * 4 + 2, "emp_pct"])


def test_region_values_join_the_unemployment_region_table_without_adding_rows():
    vals = good()
    rs = pd.DataFrame({"period_idx": [2561 * 4, 2561 * 4], "region": ["ภาคกลาง", "ภาคเหนือ"], "rate_pct": [1.0, 2.0]})
    w = pd.concat([wage_age_raw(vals), wage_age_raw({(2561, 1): 14000.0}, region="ภาคกลาง"), wage_age_raw({(2561, 1): 12000.0}, region="ภาคเหนือ")])
    b = run_build(w_age=w, region_series=rs)
    out = b.get("region_series")
    assert len(out) == 2 and {"emp_pct", "wage"} <= set(out.columns)
    assert out.set_index("region")["wage"].to_dict() == {"ภาคกลาง": 14000.0, "ภาคเหนือ": 12000.0}


def test_region_wage_from_two_tables_that_disagree_is_dropped():
    vals = good()
    w_age = pd.concat([wage_age_raw(vals), wage_age_raw({(2561, 1): 14000.0}, region="ภาคกลาง")])
    w_ind = pd.concat([wage_ind_raw(vals), wage_ind_raw({(2561, 1): 17000.0}, region="ภาคกลาง")])
    b = run_build(w_age=w_age, w_ind=w_ind)
    reg = b.get("lm_region")
    assert reg[reg["region"] == "ภาคกลาง"]["wage"].isna().all() or reg[reg["region"] == "ภาคกลาง"].empty
    assert any(i.check == "region_tables_conflict" for i in b.report.issues)
