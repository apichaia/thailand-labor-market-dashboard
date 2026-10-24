"""Turn sidebar filters into data.

Each dataset supports only some dimensions. A selector picks the table that
really contains the requested dimensions, and reports which filters it could
not honour (``ignored``) so the UI can say so instead of silently ignoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from analytics import metrics
from data_processing.normalize import EDU_ORDER
from data_processing.pipeline import PERIOD_COLS, DataBundle

SEXES = ["ชาย", "หญิง"]


@dataclass
class Filters:
    year_min: int
    year_max: int
    quarters: tuple[int, ...] = (1, 2, 3, 4)
    regions: tuple[str, ...] = ()   # empty = all
    sexes: tuple[str, ...] = ()     # empty = all
    edus: tuple[str, ...] = ()      # empty = all

    def region_active(self, universe) -> bool:
        return bool(self.regions) and set(self.regions) != set(universe)

    @property
    def sex_active(self) -> bool:
        return bool(self.sexes) and set(self.sexes) != set(SEXES)

    @property
    def edu_active(self) -> bool:
        return bool(self.edus) and set(self.edus) != set(EDU_ORDER)

    def describe(self) -> str:
        parts = [f"ปี {self.year_min}–{self.year_max}"]
        if set(self.quarters) != {1, 2, 3, 4}:
            parts.append("ไตรมาส " + ",".join(map(str, sorted(self.quarters))))
        if self.regions:
            parts.append("ภาค: " + ", ".join(self.regions))
        if self.sexes:
            parts.append("เพศ: " + ", ".join(self.sexes))
        if self.edus:
            parts.append("การศึกษา: " + ", ".join(self.edus))
        return " | ".join(parts)


@dataclass
class Selection:
    data: pd.DataFrame
    source: str = ""
    ignored: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    unavailable_reason: str | None = None

    @property
    def empty(self) -> bool:
        return self.data is None or len(self.data) == 0


def in_time(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    m = df["year_be"].between(f.year_min, f.year_max) & df["quarter"].isin(f.quarters)
    return df[m]


def all_regions(b: DataBundle) -> list[str]:
    reg = b.get("region_series")
    order = ["กรุงเทพมหานคร", "ภาคเหนือ", "ภาคตะวันออกเฉียงเหนือ", "ภาคกลาง", "ภาคใต้"]
    present = set(reg["region"]) if len(reg) else set()
    return [r for r in order if r in present] + sorted(present - set(order))


def _region_note(f: Filters, universe, notes: list[str]) -> None:
    return None  # since 2568 NSO splits ภาคกลาง/ภาคใต้ in two: the parts are added back (regions5.py), so the series stay comparable


# ---------------------------------------------------------------------------


def unemployed_series(b: DataBundle, f: Filters, *, time_filter: bool = False) -> Selection:
    """Quarterly unemployed (thousand persons) and rate under region/sex/education filters.

    Not time-filtered by default so QoQ/YoY can look back outside the window.
    """
    universe = all_regions(b)
    notes: list[str] = []
    _region_note(f, universe, notes)
    reg_on = f.region_active(universe)
    if not (f.sex_active or f.edu_active):
        d = b.get("region_series")
        if d.empty:
            return Selection(pd.DataFrame(), unavailable_reason="ไม่มีข้อมูลผู้ว่างงานรายภูมิภาค")
        if reg_on:
            d = d[d["region"].isin(f.regions)]
        g = d.groupby(PERIOD_COLS, as_index=False).agg(u_k=("u_k", "sum"), lf_k=("lf_k", lambda s: s.sum(min_count=len(s))),
                                                       rate_ok=("rate_pct", lambda s: s.notna().all()))
        g["rate_pct"] = np.where(g["rate_ok"] & (g["lf_k"] > 0), g["u_k"] / g["lf_k"] * 100, np.nan)
        # the national row carries the consistency check against the NSO-published rate
        if not reg_on:
            nat = b.get("national")[["period_idx", "rate_pct"]].rename(columns={"rate_pct": "rate_nat"})
            g = g.merge(nat, on="period_idx", how="left")
            g["rate_pct"] = g["rate_nat"]
            g = g.drop(columns="rate_nat")
        g = g.drop(columns="rate_ok")
        src = "สสช.: ผู้ว่างงานจำแนกตามภาคและเขตการปกครอง (OS_02_0003_01)"
    else:
        cube = b.get("cube")
        if cube.empty:
            return Selection(pd.DataFrame(), unavailable_reason="ไม่มีตารางข้ามมิติที่ผ่านการตรวจสอบสำหรับตัวกรองเพศ/การศึกษา")
        d = cube
        if reg_on:
            d = d[d["region"].isin(f.regions)]
        if f.sex_active:
            d = d[d["sex"].isin(f.sexes)]
        if f.edu_active:
            d = d[d["edu_group"].isin(f.edus)]
        g = d.groupby(PERIOD_COLS, as_index=False)["value_k"].sum().rename(columns={"value_k": "u_k"})
        g["lf_k"] = np.nan
        g["rate_pct"] = np.nan
        if not f.edu_active:  # rate only when the denominator matches (region x sex)
            lf = b.get("lf_region_sex")
            if len(lf):
                l2 = lf[lf["sex"].isin(f.sexes) if f.sex_active else lf["sex"].isin(SEXES)]
                if reg_on:
                    l2 = l2[l2["region"].isin(f.regions)]
                l2 = l2.groupby("period_idx")["value_k"].sum().rename("lf_k")
                g = g.drop(columns="lf_k").merge(l2, on="period_idx", how="left")
                bad = set(b.get("national").query("not quality_ok")["period_idx"])
                g["rate_pct"] = np.where((g["lf_k"] > 0) & ~g["period_idx"].isin(bad), g["u_k"] / g["lf_k"] * 100, np.nan)
        else:
            notes.append("อัตราการว่างงานเมื่อกรองระดับการศึกษา ดูได้ที่หน้า Demographic (คำนวณระดับประเทศด้วยตัวหารที่สอดคล้องกัน)")
        ex = b.excluded.get("nso_u_cube", [])
        notes.append(f"ใช้ตารางข้ามมิติ (เริ่มปี 2561) — ไตรมาสที่ตรวจยอดรวมไม่ผ่าน {len(ex)} ไตรมาสถูกยกเว้น")
        src = "สสช.: ผู้ว่างงานจำแนกตามภาค เพศ การศึกษา (OS_02_0003_02)"
    g = g.sort_values("period_idx").reset_index(drop=True)
    return Selection(g, src, [], notes)


def kpi_period(sel: Selection, f: Filters) -> int | None:
    """Latest period inside the year/quarter window that has data."""
    if sel.empty:
        return None
    w = in_time(sel.data, f)
    w = w[w["u_k"].notna()]
    return int(w["period_idx"].max()) if len(w) else None


def breakdown_education(b: DataBundle, f: Filters) -> Selection:
    universe = all_regions(b)
    reg_on, sex_on = f.region_active(universe), f.sex_active
    if not reg_on and not sex_on and b.has("u_edu"):
        d = b.get("u_edu").groupby(PERIOD_COLS + ["edu_group"], as_index=False)["value_k"].sum()
        src = "สสช.: ผู้ว่างงานจำแนกตามระดับการศึกษา (LFS_02_20536_25), 2563 เป็นต้นไป"
    elif b.has("cube"):
        d = b.get("cube")
        if reg_on:
            d = d[d["region"].isin(f.regions)]
        if sex_on:
            d = d[d["sex"].isin(f.sexes)]
        d = d.groupby(PERIOD_COLS + ["edu_group"], as_index=False)["value_k"].sum()
        src = "สสช.: ผู้ว่างงานตารางข้ามมิติ (OS_02_0003_02), 2561 เป็นต้นไป เฉพาะไตรมาสที่ตรวจสอบผ่าน"
    else:
        return Selection(pd.DataFrame(), unavailable_reason="ไม่มีข้อมูลผู้ว่างงานรายระดับการศึกษาที่ผ่านการตรวจสอบ")
    d = d.rename(columns={"value_k": "u_k"})
    if f.edu_active:
        d = d[d["edu_group"].isin(f.edus)]
    return Selection(in_time(d, f).reset_index(drop=True), src)


def breakdown_sex(b: DataBundle, f: Filters) -> Selection:
    universe = all_regions(b)
    reg_on, edu_on = f.region_active(universe), f.edu_active
    if not reg_on and not edu_on and b.has("province"):
        p = b.get("province")
        p = p[p["sex"].isin(SEXES)]
        d = p.groupby(PERIOD_COLS + ["sex"], as_index=False)["unemployed_k"].sum().rename(columns={"unemployed_k": "u_k"})
        src = "สสช.: ผู้ว่างงานรายจังหวัด×เพศ รวมทุกจังหวัด (SFD_SPB0208), 2564 เป็นต้นไป"
    elif b.has("cube"):
        d = b.get("cube")
        if reg_on:
            d = d[d["region"].isin(f.regions)]
        if edu_on:
            d = d[d["edu_group"].isin(f.edus)]
        d = d[d["sex"].isin(SEXES)].groupby(PERIOD_COLS + ["sex"], as_index=False)["value_k"].sum().rename(columns={"value_k": "u_k"})
        src = "สสช.: ผู้ว่างงานตารางข้ามมิติ (OS_02_0003_02), 2561 เป็นต้นไป เฉพาะไตรมาสที่ตรวจสอบผ่าน"
    else:
        return Selection(pd.DataFrame(), unavailable_reason="ไม่มีข้อมูลผู้ว่างงานรายเพศที่ผ่านการตรวจสอบ")
    if f.sex_active:
        d = d[d["sex"].isin(f.sexes)]
    return Selection(in_time(d, f).reset_index(drop=True), src)


def sex_rates(b: DataBundle, f: Filters) -> Selection:
    """Unemployment rate by sex = unemployed(sex) / labour force(sex), same region basis."""
    cube, lf = b.get("cube"), b.get("lf_region_sex")
    if cube.empty or lf.empty:
        return Selection(pd.DataFrame(), unavailable_reason="ข้อมูลไม่เพียงพอสำหรับคำนวณอัตราการว่างงานรายเพศ")
    universe = all_regions(b)
    reg_on = f.region_active(universe)
    u, l = cube, lf
    if reg_on:
        u, l = u[u["region"].isin(f.regions)], l[l["region"].isin(f.regions)]
    if f.edu_active:
        return Selection(pd.DataFrame(), unavailable_reason="ไม่มีตัวหารกำลังแรงงานแยกตามเพศและการศึกษาในแหล่งเดียวกันพร้อมกับภาค — ไม่คำนวณอัตรา")
    u = u[u["sex"].isin(SEXES)].groupby(PERIOD_COLS + ["sex"], as_index=False)["value_k"].sum().rename(columns={"value_k": "u_k"})
    l = l[l["sex"].isin(SEXES)].groupby(["period_idx", "sex"], as_index=False)["value_k"].sum().rename(columns={"value_k": "lf_k"})
    d = u.merge(l, on=["period_idx", "sex"], how="left")
    bad = set(b.get("national").query("not quality_ok")["period_idx"])
    d["rate_pct"] = np.where((d["lf_k"] > 0) & ~d["period_idx"].isin(bad), d["u_k"] / d["lf_k"] * 100, np.nan)
    if f.sex_active:
        d = d[d["sex"].isin(f.sexes)]
    return Selection(in_time(d, f).reset_index(drop=True),
                     "คำนวณ: ผู้ว่างงาน (OS_02_0003_02) ÷ กำลังแรงงาน (OS_02_0001_01) ตามเพศ×ภาค")


def education_rates(b: DataBundle, f: Filters) -> Selection:
    """Rate by education = U_edu / (U_edu + employed_edu) at national level.

    Region is not supported: the unemployed and employed tables use different
    regional breakdowns before 2568. This denominator excludes seasonally
    inactive labour force, so it differs from NSO's headline rate by <~0.05 pp.
    """
    universe = all_regions(b)
    if f.region_active(universe):
        return Selection(pd.DataFrame(), unavailable_reason="อัตรารายระดับการศึกษาคำนวณเฉพาะระดับประเทศ (การแบ่งภาคของตัวตั้งและตัวหารไม่ตรงกันก่อนปี 2568)")
    emp = b.get("emp_edu")
    if emp.empty or not (b.has("u_edu") or b.has("cube")):
        return Selection(pd.DataFrame(), unavailable_reason="ข้อมูลไม่เพียงพอสำหรับคำนวณอัตราการว่างงานรายระดับการศึกษา")
    if f.sex_active:
        if not b.has("cube"):
            return Selection(pd.DataFrame(), unavailable_reason="ไม่มีตารางผู้ว่างงานข้ามมิติสำหรับตัวกรองเพศ")
        u = b.get("cube")
        u = u[u["sex"].isin(f.sexes)].groupby(PERIOD_COLS + ["edu_group"], as_index=False)["value_k"].sum()
        e = emp[emp["sex"].isin(f.sexes)]
    else:
        u = b.get("u_edu").groupby(PERIOD_COLS + ["edu_group"], as_index=False)["value_k"].sum()
        e = emp
    e = e.groupby(["period_idx", "edu_group"], as_index=False)["value_k"].sum().rename(columns={"value_k": "emp_k"})
    d = u.rename(columns={"value_k": "u_k"}).merge(e, on=["period_idx", "edu_group"], how="inner", validate="one_to_one")
    d["rate_pct"] = np.where(d["u_k"] + d["emp_k"] > 0, d["u_k"] / (d["u_k"] + d["emp_k"]) * 100, np.nan)
    if f.edu_active:
        d = d[d["edu_group"].isin(f.edus)]
    return Selection(in_time(d, f).reset_index(drop=True), "คำนวณ: ผู้ว่างงาน ÷ (ผู้ว่างงาน + ผู้มีงานทำ) ตามระดับการศึกษา, 2563 เป็นต้นไป")


def age_breakdown(b: DataBundle, f: Filters) -> Selection:
    u = b.get("u_age")
    if u.empty:
        return Selection(pd.DataFrame(), unavailable_reason="ไม่มีข้อมูลผู้ว่างงานรายกลุ่มอายุที่ผ่านการตรวจสอบ")
    ign = []
    universe = all_regions(b)
    if f.region_active(universe):
        u = u[u["region"].isin(f.regions)]
    if f.sex_active:
        ign.append("เพศ")
    if f.edu_active:
        ign.append("ระดับการศึกษา")
    d = u.groupby(PERIOD_COLS + ["age_group", "status"], as_index=False)["value_k"].sum().rename(columns={"value_k": "u_k"})
    return Selection(in_time(d, f).reset_index(drop=True), "สสช.: ผู้ว่างงานจำแนกกลุ่มอายุ สถานภาพ (OS_02_0003_04)", ign)


def published_age_rates(b: DataBundle, f: Filters) -> Selection:
    r = b.get("rates_pub")
    if r.empty:
        return Selection(pd.DataFrame(), unavailable_reason="ไม่มีตารางอัตราการว่างงานที่ สสช. เผยแพร่")
    d = r[(r["region"] == "ทั่วประเทศ") & (r["area"] == "รวม") & (r["sex"] == "รวม") & (r["age_group"] != "รวม")]
    return Selection(in_time(d, f).reset_index(drop=True), "สสช.: อัตราการว่างงานตามกลุ่มอายุ (ตามที่เผยแพร่)",
                     [x for x, on in (("เพศ", f.sex_active), ("ภาค", f.region_active(all_regions(b))), ("ระดับการศึกษา", f.edu_active)) if on])


def regional_snapshot(b: DataBundle, f: Filters, period_idx: int) -> Selection:
    d = b.get("region_series")
    d = d[d["period_idx"] == period_idx]
    if d.empty:
        return Selection(pd.DataFrame(), unavailable_reason="ไม่มีข้อมูลภูมิภาคในไตรมาสที่เลือก")
    ign = [x for x, on in (("เพศ", f.sex_active), ("ระดับการศึกษา", f.edu_active)) if on]
    return Selection(d.reset_index(drop=True), "สสช.: ผู้ว่างงานรายภาค (OS_02_0003_01) ÷ กำลังแรงงานรายภาค (OS_02_0001_01)", ign)


def region_trend(b: DataBundle, f: Filters) -> Selection:
    d = b.get("region_series")
    if d.empty:
        return Selection(pd.DataFrame(), unavailable_reason="ไม่มีข้อมูลภูมิภาค")
    if f.region_active(all_regions(b)):
        d = d[d["region"].isin(f.regions)]
    ign = [x for x, on in (("เพศ", f.sex_active), ("ระดับการศึกษา", f.edu_active)) if on]
    return Selection(in_time(d, f).reset_index(drop=True), "สสช.: OS_02_0003_01 และ OS_02_0001_01", ign)


def province_snapshot(b: DataBundle, period_idx: int, sexes=("รวม",)) -> Selection:
    p = b.get("province")
    if p.empty:
        return Selection(pd.DataFrame(), unavailable_reason="ไม่มีข้อมูลรายจังหวัดที่ผ่านการตรวจสอบ")
    d = p[(p["period_idx"] == period_idx) & (p["sex"].isin(sexes))]
    if d.empty:
        return Selection(pd.DataFrame(), unavailable_reason="ไม่มีข้อมูลรายจังหวัดในไตรมาสที่เลือก (ข้อมูลรายจังหวัดเริ่มปี 2564)")
    return Selection(d.reset_index(drop=True), "สสช.: ผู้ว่างงานและอัตราการว่างงานรายจังหวัด (SFD_SPB0208)")


def economic_frame(b: DataBundle, f: Filters, *, exclude_flagged: bool = True) -> tuple[pd.DataFrame, list[str]]:
    """National unemployment x GDP growth, joined on quarter. Region/sex/edu filters do not apply."""
    notes = []
    nat, gdp = b.get("national"), b.get("gdp")
    if nat.empty or gdp.empty:
        return pd.DataFrame(), ["ไม่มีข้อมูลเพียงพอ (ต้องมีทั้งอัตราการว่างงานและ GDP)"]
    merged, rep = metrics.merge_economic_indicators(nat, gdp)
    if not rep.ok or merged.empty:
        return pd.DataFrame(), [i.message for i in rep.errors] or ["ไม่มีช่วงเวลาที่ตรงกัน"]
    merged = metrics.add_changes(merged.rename(columns={"rate_pct": "rate_pct"}), "rate_pct")
    merged = merged.rename(columns={"yoy_abs": "rate_yoy_pp"})
    if exclude_flagged:
        merged.loc[~merged["quality_ok"], ["rate_pct", "rate_yoy_pp"]] = np.nan
    return in_time(merged, f).reset_index(drop=True), notes


def region_map_frame(b: DataBundle, f: Filters, idx: int, column: str) -> Selection:
    """Every province gets the value of the region NSO assigned it to in that year.

    ``column`` is 'u_k' (unemployed, thousand) or 'rate_pct'. Regions outside the region filter,
    or without a value for that quarter, stay empty (NaN) - nothing is estimated.
    """
    if b.geo is None or not b.has("province_region"):
        return Selection(pd.DataFrame(), unavailable_reason="ไม่มีข้อมูลขอบเขตจังหวัดหรือนิยามจังหวัด→ภาคที่ผ่านการตรวจสอบ")
    year = idx // 4
    m = b.get("province_region")
    m = m[m["year_be"] == year]
    if m.empty:
        ys = sorted(b.get("province_region")["year_be"].unique())
        return Selection(pd.DataFrame(), unavailable_reason=f"ไม่มีนิยามจังหวัด→ภาคของ สสช. สำหรับปี {year} (มีปี {ys[0]}–{ys[-1]}) จึงไม่วาดแผนที่ปีนี้")
    r = b.get("region_series")
    cols = ["region", "u_k", "rate_pct"] + [x for x in (column,) if x not in ("u_k", "rate_pct") and x in r.columns]
    r = r[r["period_idx"] == idx][cols]
    d = m.merge(r, on="region", how="left")
    d["value"] = d[column]
    if f.region_active(all_regions(b)):
        d.loc[~d["region"].isin(f.regions), "value"] = np.nan
    notes = []
    if year >= 2568:
        notes.append("ตั้งแต่ปี 2568 สสช. แยกภาคตะวันออกและภาคใต้ชายแดนออกมา แดชบอร์ดรวมกลับเป็น 5 ภาค (ผู้ว่างงานรวมได้ตรง ๆ; อัตรามีงานทำและค่าจ้างของภาคกลางและภาคใต้รวมไม่ได้ จึงเป็นช่องว่าง)")
    return Selection(d.reset_index(drop=True), "สสช.: ผู้ว่างงานรายภาค (OS_02_0003_01), กำลังแรงงาน (OS_02_0001_01), จังหวัด→ภาค (ST_02_2005005_4)",
                     notes=notes)


def _headcount_series(hc: pd.DataFrame, regions: list[str], sexes: list[str]) -> pd.DataFrame:
    """Employed persons (million) for the picked regions / sexes: the file has region x sex x age rows, so any mix can be added up.
    Only quarters where every group is present are kept (no partial sums)."""
    if hc is None or len(hc) == 0:
        return pd.DataFrame(columns=["period_idx", "emp_k", "emp_m"])
    sub = hc[hc["area"] == "รวม"]
    if regions:
        sub = sub[sub["region"].isin(regions)]
    if sexes:
        sub = sub[sub["sex"].isin(sexes)]
    g = sub.groupby("period_idx").agg(emp_k=("emp_k", "sum"), n=("emp_k", "size"))
    need = (len(regions) or 5) * (len(sexes) or 2) * 8
    g = g[g["n"] == need].reset_index()[["period_idx", "emp_k"]]
    return g.assign(emp_m=g["emp_k"] / 1000.0)


def lm_scoped_series(b: DataBundle, f: Filters):
    """Series for the employment / wage / employed-persons cards that follow the sidebar filters.

    Employment rate and wage are published for one region or for one sex, not for several regions or a region together
    with a sex: then they stay national and say so (nothing is averaged). Employed persons come from the file with
    region x sex x age rows, so they follow every region / sex combination. The scope of that series is in ``hcm.attrs``."""
    lmn, lmr, lms, hc = b.get("lm_national"), b.get("lm_region"), b.get("lm_sex_age"), b.get("lm_headcount")
    nat_hc = b.get("lm_employed_national")
    nat_hc = nat_hc.assign(emp_m=nat_hc["emp_k"] / 1000.0) if len(nat_hc) else nat_hc
    emp, wage = lmn, lmn
    scope, notes = "ทั่วประเทศ", []
    regions, sexes = list(f.regions), list(f.sexes)
    if len(regions) == 1 and not sexes and len(lmr):
        emp = wage = lmr[lmr["region"] == regions[0]]
        scope = regions[0]
    elif len(sexes) == 1 and not regions and len(lms):
        emp = wage = lms[(lms["sex"] == sexes[0]) & (lms["age_group"] == "รวม")]
        scope = f"เพศ{sexes[0]}"
    elif regions or sexes:
        notes.append("ตัวกรองภาคหลายภาค หรือภาคร่วมกับเพศ ไม่มีตารางอัตรามีงานทำ/ค่าจ้างที่เผยแพร่เป็นตัวเลขเดียว จึงแสดงระดับประเทศ (จำนวนผู้มีงานทำยังตามตัวกรอง)")
    if regions or sexes:
        hcm = _headcount_series(hc, regions, sexes)
        hc_scope = " · ".join(x for x in (", ".join(regions), ("เพศ" + ", ".join(sexes)) if sexes else "") if x)
    else:
        hcm, hc_scope = nat_hc, "ทั่วประเทศ"
    hcm = hcm.copy() if hcm is not None else hcm
    if hcm is not None:
        hcm.attrs["scope"] = hc_scope
    if f.edu_active:
        notes.append("ตัวกรองการศึกษาไม่มีผลกับการ์ดมีงานทำ ค่าจ้าง และผู้มีงานทำ")
    return emp, wage, hcm, scope, notes


def quarter_ok(idxs, f: Filters) -> list[int]:
    """Keep the period indexes whose quarter is ticked in the sidebar."""
    return [int(i) for i in idxs if (int(i) % 4 + 1) in f.quarters]
