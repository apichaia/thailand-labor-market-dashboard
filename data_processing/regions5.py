"""Present every regional table on the same five regions: กรุงเทพมหานคร, กลาง, เหนือ, ตะวันออกเฉียงเหนือ, ใต้.

From 2568 NSO splits two of them (ภาคกลาง -> กลาง + ตะวันออก, ภาคใต้ -> ใต้ + ใต้ชายแดน). The province lists were
checked: 25 = 17 + 8 and 14 = 11 + 3, with exactly the same provinces, so the two parts can be added back together.

* counts (unemployed, labour force, employed persons) are summed; the unemployment rate is recomputed from the sums
  (exact, and it is comparable across the 2567/2568 break);
* the employment rate and the average wage cannot be added without the population / the number of employees of
  each part: for the merged regions in 2568+ they stay empty (nothing is estimated).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MERGE = {"ภาคตะวันออก": "ภาคกลาง", "ภาคใต้ชายแดน": "ภาคใต้"}
FIVE = ["กรุงเทพมหานคร", "ภาคกลาง", "ภาคเหนือ", "ภาคตะวันออกเฉียงเหนือ", "ภาคใต้"]
BASIS = "5 ภาค"


def _merge(df: pd.DataFrame, keys: list[str], sums: list[str], blank: list[str], rate: tuple[str, str, str] | None = None) -> pd.DataFrame:
    """Rename the split regions to their parent and collapse. ``blank`` columns become NaN where parts were added."""
    if df is None or len(df) == 0 or "region" not in df.columns:
        return df
    d = df.copy()
    d["region"] = d["region"].replace(MERGE)
    group = [k for k in keys if k in d.columns]
    keep = [c for c in d.columns if c not in group and c not in sums and c not in blank]
    agg = {s: (s, lambda x: x.sum(min_count=len(x))) for s in sums if s in d.columns}
    agg["_n"] = (group[-1], "size")
    for c in keep + [x for x in blank if x in d.columns]:
        agg[c] = (c, "first")
    out = d.groupby(group, as_index=False, sort=False).agg(**agg)
    merged = out["_n"] > 1
    for c in blank:
        if c in out.columns:
            out.loc[merged, c] = np.nan
    if rate:
        num, den, col = rate
        if num in out.columns and den in out.columns:
            ok = merged & out[den].gt(0) & out[num].notna()
            out.loc[ok, col] = out.loc[ok, num] / out.loc[ok, den] * 100
            out.loc[merged & ~ok, col] = np.nan
    out = out.drop(columns="_n")
    if "region_basis" in out.columns:
        out["region_basis"] = BASIS
    return out[[c for c in df.columns if c in out.columns]]


def collapse(b) -> None:
    t = b.tables
    if "region_series" in t:
        t["region_series"] = _merge(t["region_series"], ["period_idx", "region"], ["u_k", "lf_k"], ["emp_pct", "wage"],
                                    rate=("u_k", "lf_k", "rate_pct")).sort_values(["period_idx", "region"]).reset_index(drop=True)
    if "lm_region" in t:
        t["lm_region"] = _merge(t["lm_region"], ["period_idx", "region"], [], ["emp_pct", "wage"]).sort_values(["period_idx", "region"]).reset_index(drop=True)
    if "province_region" in t:
        pr = t["province_region"].copy()
        pr["region"] = pr["region"].replace(MERGE)
        t["province_region"] = pr
    if "lm_headcount" in t:
        t["lm_headcount"] = _merge(t["lm_headcount"], ["period_idx", "region", "area", "sex", "age_group"], ["emp_k"], [])
