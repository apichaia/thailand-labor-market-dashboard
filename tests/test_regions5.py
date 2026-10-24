"""The seven post-2568 regions are shown as the five long-standing ones, without inventing numbers."""
import numpy as np
import pandas as pd

from data_processing import regions5
from data_processing.pipeline import DataBundle


def _bundle():
    rows = []
    for region, u, lf, emp in [("ภาคกลาง", 10.0, 1000.0, 70.0), ("ภาคตะวันออก", 5.0, 500.0, 75.0), ("ภาคเหนือ", 4.0, 400.0, 66.0),
                               ("ภาคใต้", 6.0, 600.0, 71.0), ("ภาคใต้ชายแดน", 3.0, 200.0, 65.0)]:
        rows.append(dict(year_be=2568, quarter=1, period_idx=10272, period_label="ไตรมาส 1/2568", region=region, region_basis="7 ภาค",
                         u_k=u, lf_k=lf, rate_pct=u / lf * 100, emp_pct=emp, wage=15000.0))
    b = DataBundle()
    b.tables["region_series"] = pd.DataFrame(rows)
    b.tables["lm_region"] = b.tables["region_series"][["period_idx", "region", "emp_pct", "wage", "year_be", "quarter", "period_label", "region_basis"]].copy()
    return b


def test_counts_are_added_and_rate_recomputed():
    b = _bundle()
    regions5.collapse(b)
    r = b.get("region_series").set_index("region")
    assert set(r.index) == {"ภาคกลาง", "ภาคเหนือ", "ภาคใต้"}
    assert r.loc["ภาคกลาง", "u_k"] == 15.0 and r.loc["ภาคกลาง", "lf_k"] == 1500.0
    assert abs(r.loc["ภาคกลาง", "rate_pct"] - 1.0) < 1e-9
    assert abs(r.loc["ภาคใต้", "rate_pct"] - 9 / 800 * 100) < 1e-9
    assert (r["region_basis"] == "5 ภาค").all()


def test_employment_rate_and_wage_are_not_averaged_for_merged_regions():
    b = _bundle()
    regions5.collapse(b)
    r = b.get("region_series").set_index("region")
    assert np.isnan(r.loc["ภาคกลาง", "emp_pct"]) and np.isnan(r.loc["ภาคใต้", "wage"])
    assert r.loc["ภาคเหนือ", "emp_pct"] == 66.0   # a region that was never split keeps its published value
    assert np.isnan(b.get("lm_region").set_index("region").loc["ภาคกลาง", "emp_pct"])
