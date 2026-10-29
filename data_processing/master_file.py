"""Employed persons (พันคน) by region x sex x age group, from NSO table OS_02_0002_01 (dataset 0706_02_0002 on data.go.th).

The cleaner also accepts the older compiled file (numbered labels such as '1) กรุงเทพมหานคร', a 'Total' region, rows with quarter 0 and
repeated keys), so every number is checked before use:
* labels are normalised, quarter 0 rows (no quarter) and repeated keys are dropped (reported);
* the sum over ages for each quarter x region x sex must match NSO's employed-persons table (LFS_02_20535_1) within 1 %.
  Groups that do not match are dropped; years without that NSO table (before 2563) cannot be checked and are labelled so.
Nothing is estimated.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import config
from data_processing import clean as c
from data_processing import normalize as nz
from data_processing import validation as v

TABLE = "nso_emp_age_sex"   # same key as the source in config.SOURCES
AGES = ["15-19 ปี", "20-24 ปี", "25-29 ปี", "30-34 ปี", "35-39 ปี", "40-49 ปี", "50-59 ปี", "60 ปีขึ้นไป"]


def _age(x):
    s = nz.normalize_age_group(x)
    return "60 ปีขึ้นไป" if s is not None and s.startswith("60") else s


def clean_headcount(raw: pd.DataFrame, table: str = TABLE):
    """-> (tidy employed-persons table, report). Columns: period cols, region, area, sex, age_group, emp_k."""
    df = nz.normalize_column_names(raw)
    rep = v.ValidationReport()
    rep.add(v.check_not_empty(df, table))
    rep.add(v.check_required_columns(df, ["year", "quarter", "region", "area", "sex", "age_group", "emp_headcount"], table))
    if not rep.ok:
        return c._fail(rep)
    rep.add(v.check_numeric(df, ["emp_headcount"], table))
    n_all = len(df)
    df = df.assign(emp_k=pd.to_numeric(df["emp_headcount"], errors="coerce")).dropna(subset=["emp_k"])
    if nz.year_era(df["year"]) != "BE":
        rep.add(v.Issue("error", "year_era", table, "ปีในตารางไม่ใช่ พ.ศ. ทั้งหมด"))
        return c._fail(rep)
    q0 = pd.to_numeric(df["quarter"], errors="coerce").fillna(0).astype(int) == 0
    if q0.any():
        rep.add(v.Issue("warning", "no_quarter", table, f"ตัดแถวที่ไม่มีไตรมาส (ไตรมาส 0) {int(q0.sum())} แถว", int(q0.sum())))
        df = df[~q0]
    df = nz.add_period_columns(df)
    df["region"] = df["region"].map(lambda x: "ทั่วประเทศ" if str(x).strip().lower() == "total" else nz.normalize_region(x))
    df["sex"] = df["sex"].map(nz.normalize_sex)
    df["age_group"] = df["age_group"].map(_age)
    # rows without an area column value are the all-areas figure (they match NSO's region x sex totals)
    df["area"] = df["area"].map(nz.normalize_area).fillna("รวม")
    df = df[df["sex"].isin(["ชาย", "หญิง"]) & df["age_group"].isin(AGES) & ~df["region"].isin(["ทั่วประเทศ", "รวม"]) & (df["emp_k"] > 0)]
    keys = ["period_idx", "region", "area", "sex", "age_group"]
    # Bangkok is entirely municipal: its only area row is its total (same rule as the NSO tables)
    bkk = df[(df["region"] == "กรุงเทพมหานคร")]
    have = set(map(tuple, bkk.loc[bkk["area"] == "รวม", ["period_idx", "sex", "age_group"]].to_numpy().tolist()))
    muni = bkk[bkk["area"] == "ในเขตเทศบาล"]
    add = muni[[tuple(r) not in have for r in muni[["period_idx", "sex", "age_group"]].to_numpy().tolist()]]
    if len(add):
        df = pd.concat([df, add.assign(area="รวม")], ignore_index=True)
    dup = df.duplicated(keys, keep=False)
    if dup.any():
        g = df[dup].groupby(keys)["emp_k"].agg(["min", "max"])
        conflict = g[(g["max"] - g["min"]) > 0.05]
        rep.add(v.Issue("warning", "duplicates", table, f"คีย์ซ้ำ {len(g)} คีย์ (ค่าขัดแย้ง {len(conflict)}) — ไม่ใช้คีย์ที่ขัดแย้ง", len(g)))
        df = df.merge(conflict[[]].reset_index().assign(_bad=True), on=keys, how="left")
        df = df[df["_bad"].isna()].drop(columns="_bad").drop_duplicates(keys)
    df = df[["year_be", "quarter", "period_idx", "period_label", "date", "region", "area", "sex", "age_group", "emp_k"]]
    df = c._add_region_basis(df) if len(df) else df
    rep.add(v.Issue("info", "rows", table, f"ใช้ได้ {len(df):,} จาก {n_all:,} แถวของตาราง", len(df)))
    if df.empty:
        rep.add(v.Issue("error", "empty", table, "ไม่มีแถวที่ใช้ได้หลังตรวจสอบ"))
        return c._fail(rep)
    return df.sort_values(keys).reset_index(drop=True), rep


def reconcile_with_nso(df: pd.DataFrame, nso_emp: pd.DataFrame | None, table: str = TABLE):
    """Drop (quarter, region, sex) groups whose age-sum disagrees with NSO. Returns (df, report, unchecked quarters)."""
    rep = v.ValidationReport()
    total = df[df["area"] == "รวม"]
    mine = total.groupby(["period_idx", "region", "sex"])["emp_k"].agg(["sum", "count"])
    full = mine["count"] == len(AGES)
    if (~full).any():
        rep.add(v.Issue("warning", "incomplete", table, f"กลุ่ม (ไตรมาส×ภาค×เพศ) ที่กลุ่มอายุไม่ครบ {int((~full).sum())} กลุ่ม — ไม่ใช้", int((~full).sum())))
    mine = mine[full]["sum"]
    if nso_emp is None or nso_emp.empty:
        rep.add(v.Issue("info", "unchecked", table, "ไม่มีตารางผู้มีงานทำของ สสช. ให้ตรวจเทียบ — จำนวนผู้มีงานทำทุกไตรมาสยังตรวจไม่ได้", len(mine)))
        keep = mine.index
        return _restrict(df, keep), rep, sorted({int(i[0]) for i in keep})
    ref = nso_emp[nso_emp["sex"].isin(["ชาย", "หญิง"])].groupby(["period_idx", "region", "sex"])["value_k"].sum()
    j = pd.concat([mine.rename("m"), ref.rename("r")], axis=1)
    both = j.dropna()
    bad = both.index[((both["m"] - both["r"]).abs() > np.maximum(config.HEADCOUNT_ABS_TOL, config.HEADCOUNT_TOL * both["r"].abs())).to_numpy()]
    if len(bad):
        per = sorted({int(i[0]) for i in bad})
        rep.add(v.Issue("warning", "reconciliation", table,
                        f"จำนวนผู้มีงานทำในตาราง OS_02_0002_01 ไม่ตรงกับ สสช. (LFS_02_20535_1) {len(bad)} กลุ่ม (ไตรมาส×ภาค×เพศ) ใน "
                        + ", ".join(nz.period_label(p // 4, p % 4 + 1) for p in per[:4]) + " — ไม่ใช้กลุ่มเหล่านั้น", len(bad), {"periods": per}))
    unchecked_idx = j.index[j["r"].isna()]
    keep = mine.index.difference(pd.Index(bad))
    checked = sorted({int(i[0]) for i in both.index.difference(pd.Index(bad))})
    unchecked = sorted({int(i[0]) for i in unchecked_idx} - set(checked))
    if unchecked:
        rep.add(v.Issue("info", "unchecked", table,
                        f"ไตรมาสที่ สสช. ไม่มีตารางอ้างอิง ({nz.period_label(unchecked[0] // 4, unchecked[0] % 4 + 1)} ถึง "
                        f"{nz.period_label(unchecked[-1] // 4, unchecked[-1] % 4 + 1)}, {len(unchecked)} ไตรมาส) ใช้ได้แต่ยังตรวจกับ สสช. ไม่ได้", len(unchecked)))
    return _restrict(df, keep), rep, unchecked


def _restrict(df: pd.DataFrame, keep_idx: pd.Index) -> pd.DataFrame:
    keys = pd.MultiIndex.from_frame(df[["period_idx", "region", "sex"]])
    return df[keys.isin(keep_idx)].reset_index(drop=True)


def national_employed(df: pd.DataFrame) -> pd.DataFrame:
    """National employed persons per quarter = sum over every region, sex and age (regions partition the country).
    A quarter is kept only when all of its (region x sex) groups are present for one regional basis."""
    t = df[df["area"] == "รวม"]
    g = t.groupby(["period_idx", "region_basis"]).agg(emp_k=("emp_k", "sum"), n=("emp_k", "size"), regions=("region", "nunique"))
    need = g.index.get_level_values("region_basis").map({"5 ภาค": 5, "7 ภาค": 7})
    ok = (g["regions"].to_numpy() == need.to_numpy()) & (g["n"].to_numpy() == need.to_numpy() * 2 * len(AGES))
    out = g[ok].reset_index().drop_duplicates("period_idx")[["period_idx", "region_basis", "emp_k"]]
    return out.sort_values("period_idx").reset_index(drop=True)


def plausibility(emp_national: pd.DataFrame, national: pd.DataFrame, table: str = TABLE) -> list[v.Issue]:
    """Employed + unemployed should be close to the labour force (the rest are people waiting for the season)."""
    if emp_national is None or emp_national.empty or national is None or national.empty:
        return []
    j = emp_national.set_index("period_idx")[["emp_k"]].join(national.set_index("period_idx")[["u_k", "lf_k"]]).dropna()
    if j.empty:
        return []
    gap = ((j["emp_k"] + j["u_k"] - j["lf_k"]).abs() / j["lf_k"]) * 100
    out = [v.Issue("info", "plausibility", table,
                   f"ผู้มีงานทำ (OS_02_0002_01) + ผู้ว่างงาน เทียบกำลังแรงงานรวมของ สสช. ต่างกันเฉลี่ย {gap.median():.2f}% สูงสุด {gap.max():.2f}% ({len(j)} ไตรมาส) "
                   "ส่วนต่างส่วนใหญ่คือผู้รอฤดูกาล ซึ่งนับในกำลังแรงงานแต่ไม่ใช่ผู้มีงานทำหรือผู้ว่างงาน", len(j))]
    bad = gap[gap > 2.0]
    if len(bad):
        out.append(v.Issue("warning", "plausibility", table,
                           "ไตรมาสที่ผู้มีงานทำ + ผู้ว่างงาน ต่างจากกำลังแรงงานเกิน 2%: "
                           + ", ".join(nz.period_label(int(i) // 4, int(i) % 4 + 1) for i in bad.index[:6]) + " (ควรตีความจำนวนผู้มีงานทำของไตรมาสเหล่านี้ด้วยความระมัดระวัง)", len(bad)))
    return out
