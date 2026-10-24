"""The friend's merged file: only the employed-persons column is used, after cleaning and a check against NSO."""
import numpy as np
import pandas as pd
import pytest

from data_processing import master_file as mf

AGES = mf.AGES


def raw_rows(year=2563, quarter=1, region="ภาคกลาง", area=None, value=100.0, sexes=("ชาย", "หญิง"), ages=AGES):
    return [{"year": year, "quarter": quarter, "region": region, "area": area, "sex": s, "age_group": a,
             "avg_wage": np.nan, "emp_rate": np.nan, "emp_headcount": value, "unemp_rate": np.nan} for s in sexes for a in ages]


def nso(region, sex_value, year=2563, quarter=1):
    idx = year * 4 + quarter - 1
    return pd.DataFrame([{"period_idx": idx, "region": region, "sex": s, "value_k": v} for s, v in sex_value.items()])


def test_labels_quarter_zero_and_conflicting_repeats_are_cleaned():
    rows = pd.DataFrame(raw_rows(region="2) ภาคกลาง") + raw_rows(quarter=0) + raw_rows(region="Total"))
    rows.loc[0, "age_group"] = "60 ขึ้นไป"                     # old spelling
    rows = pd.concat([rows, rows.iloc[[3]].assign(emp_headcount=999.0)], ignore_index=True)   # conflicting repeat of one key
    out, rep = mf.clean_headcount(rows)
    assert set(out["region"]) == {"ภาคกลาง"}                  # 'Total' and the numbered label handled, quarter 0 dropped
    assert (out["period_idx"] == 2563 * 4).all()
    assert any(i.check == "no_quarter" for i in rep.issues)
    assert any(i.check == "duplicates" for i in rep.issues)
    assert len(out) == 14   # 16 keys - 1 (row 0 re-labelled, so 15-19 male is absent) - 1 (conflicting key removed, never averaged)


def test_rows_without_area_are_the_all_areas_figure_and_bangkok_municipal_is_its_total():
    rows = pd.DataFrame(raw_rows(region="กรุงเทพมหานคร", area="ในเขตเทศบาล"))
    out, _ = mf.clean_headcount(rows)
    assert set(out["area"]) == {"ในเขตเทศบาล", "รวม"}
    out2, _ = mf.clean_headcount(pd.DataFrame(raw_rows()))
    assert set(out2["area"]) == {"รวม"}


def test_groups_that_disagree_with_nso_are_dropped_and_old_years_stay_unchecked():
    good, _ = mf.clean_headcount(pd.DataFrame(raw_rows(sexes=("ชาย",)) + raw_rows(sexes=("หญิง",), value=50.0)))
    ref = nso("ภาคกลาง", {"ชาย": 800.0, "หญิง": 400.0})          # 8 ages x 100 = 800, 8 x 50 = 400 -> match
    kept, rep, unchecked = mf.reconcile_with_nso(good, ref)
    assert len(kept) == 16 and unchecked == []
    ref_bad = nso("ภาคกลาง", {"ชาย": 800.0, "หญิง": 900.0})       # women disagree
    kept, rep, _ = mf.reconcile_with_nso(good, ref_bad)
    assert set(kept["sex"]) == {"ชาย"} and any(i.check == "reconciliation" for i in rep.issues)
    old, _ = mf.clean_headcount(pd.DataFrame(raw_rows(year=2557)))
    kept, rep, unchecked = mf.reconcile_with_nso(old, ref)       # NSO has no table for 2557
    assert len(kept) == 16 and unchecked == [2557 * 4]


def test_national_total_needs_every_region_of_one_basis():
    five = ["กรุงเทพมหานคร", "ภาคกลาง", "ภาคเหนือ", "ภาคตะวันออกเฉียงเหนือ", "ภาคใต้"]
    full, _ = mf.clean_headcount(pd.DataFrame(sum((raw_rows(region=r) for r in five), [])))
    assert mf.national_employed(full)["emp_k"].iloc[0] == pytest.approx(5 * 16 * 100.0)
    partial, _ = mf.clean_headcount(pd.DataFrame(sum((raw_rows(region=r) for r in five[:4]), [])))
    assert mf.national_employed(partial).empty                    # a missing region never gives a smaller 'national' number
