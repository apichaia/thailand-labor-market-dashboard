"""Raw files -> validated, analysis-ready tables (the DataBundle).

Order of work:
1. read each raw file and run its cleaner (schema / unit / duplicates / era);
2. build the national benchmark (sum of region x area, a partition -> no double count);
3. reconcile every other breakdown against the benchmark, per quarter;
4. compute unemployment rates from counts / labour force and compare with the
   rate NSO publishes.
Raw data is never modified; processed tables are written separately.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

import config
from data_processing import clean as c
from data_processing import labour_market as lm
from data_processing import master_file as mf
from data_processing import normalize as nz
from data_processing import intro_payload, regions5
from data_processing import validation as v
from data_sources import downloader as dl

log = logging.getLogger(__name__)

PERIOD_COLS = ["year_be", "quarter", "period_idx", "period_label", "date"]


@dataclass
class DataBundle:
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    report: v.ValidationReport = field(default_factory=v.ValidationReport)
    availability: dict[str, dict] = field(default_factory=dict)
    excluded: dict[str, list[int]] = field(default_factory=dict)  # table -> excluded period_idx
    geo: dict | None = None  # province boundaries (GeoJSON, keyed by ISO code)

    def get(self, name: str) -> pd.DataFrame:
        return self.tables.get(name, pd.DataFrame())

    def has(self, name: str) -> bool:
        return name in self.tables and len(self.tables[name]) > 0

    @property
    def latest_period_idx(self) -> int | None:
        nat = self.get("national")
        return int(nat["period_idx"].max()) if len(nat) else None

    @property
    def usable(self) -> bool:
        return self.has("national") and self.has("region_series")


def restrict_from(b: DataBundle, start_be: int) -> DataBundle:
    """A copy of the bundle with every table cut to the quarters from year ``start_be`` on (period_idx = year_be * 4 + quarter - 1).
    Nothing is estimated: rows are only dropped. Tables without period_idx (province boundaries, labels) are kept as they are."""
    lo = start_be * 4
    tables = {k: (df[df["period_idx"] >= lo].reset_index(drop=True) if "period_idx" in df.columns else df) for k, df in b.tables.items()}
    for k, df in tables.items():
        if k in b.tables and "period_idx" in df.columns:
            df.attrs = dict(b.tables[k].attrs)
    return DataBundle(tables=tables, report=b.report, availability=b.availability,
                      excluded={k: [p for p in v if p >= lo] for k, v in b.excluded.items()}, geo=b.geo)


def _load(key: str, cleaner, bundle: DataBundle, raw_dir: Path, *, path_based=False, encoding="utf-8-sig"):
    spec = config.SOURCES_BY_KEY[key]
    path = dl.raw_path(spec, raw_dir)
    if not path.exists():
        bundle.availability[key] = {"ok": False, "rows": 0, "reason": "ยังไม่มีไฟล์ข้อมูลดิบ (ยังไม่เคยดาวน์โหลดสำเร็จ)", "kind": "missing"}
        return None
    try:
        df, rep = cleaner(path) if path_based else cleaner(c.read_raw_csv(path, encoding))
    except Exception as exc:  # unreadable file is a data problem, reported not hidden
        log.exception("cannot read %s", key)
        rep = v.ValidationReport().add(v.Issue("error", "read", key, f"อ่านไฟล์ไม่ได้: {type(exc).__name__}"))
        df = pd.DataFrame()
    bundle.report.extend(rep)
    ok = rep.ok and len(df) > 0
    bundle.availability[key] = {"ok": ok, "rows": len(df), "kind": "ok" if ok else "validation",
                                "reason": None if ok else "; ".join(i.message for i in rep.errors) or "ข้อมูลว่าง"}
    return df if ok else None


def _by_period(df, value, extra=()):
    keys = ["period_idx"] + list(extra)
    return df.groupby(keys)[value].sum(min_count=1)


def _periods_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df[PERIOD_COLS].drop_duplicates("period_idx").sort_values("period_idx")


def build_dashboard_data(raw_dir: Path | None = None) -> DataBundle:
    raw_dir = Path(raw_dir or config.DATA_RAW)
    b = DataBundle()
    u_reg = _load("nso_u_region", c.clean_u_region, b, raw_dir)
    lf_os = _load("nso_lf_region_area_sex", c.clean_lf_region_area_sex, b, raw_dir)
    cube = _load("nso_u_cube", c.clean_u_cube, b, raw_dir)
    u_edu = _load("nso_u_edu", c.clean_u_edu, b, raw_dir)
    u_age = _load("nso_u_age_status", c.clean_u_age, b, raw_dir)
    prov = _load("nso_u_province", c.clean_u_province, b, raw_dir)
    lf_rs = _load("nso_lf_region_sex", c.clean_lf_region_sex, b, raw_dir)
    emp_edu = _load("nso_emp_region_sex_edu", c.clean_emp_region_sex_edu, b, raw_dir)
    rate_old = _load("nso_rate_old", lambda d: c.clean_rates(d, "nso_rate_old"), b, raw_dir)
    rate_new = _load("nso_rate_new", lambda d: c.clean_rates(d, "nso_rate_new"), b, raw_dir)
    gdp = _load("nesdc_gdp", c.clean_gdp, b, raw_dir, path_based=True)
    sso = _load("sso_benefit", c.clean_sso, b, raw_dir, path_based=True)
    bot = _load("bot_reasons", c.clean_bot_reasons, b, raw_dir, path_based=True)
    prov_reg = _load("nso_province_region", c.clean_province_region, b, raw_dir)
    geo = _load("geo_provinces", c.clean_geo, b, raw_dir, path_based=True)
    emp_ref = _load("nso_emp_region_sex", c.clean_emp_region_sex, b, raw_dir)
    lm_tables = {
        "er_sa": _load("nso_er_sex_age", lm.clean_emp_sex_age, b, raw_dir),
        "er_edu": _load("nso_er_edu", lm.clean_emp_edu, b, raw_dir),
        "er_rs": _load("nso_er_region_sex", lm.clean_emp_region_sex, b, raw_dir),
        "w_age": _load("nso_w_age", lm.clean_wage_age, b, raw_dir),
        "w_edu": _load("nso_w_edu", lm.clean_wage_edu, b, raw_dir),
        "w_ind": _load("nso_w_industry", lm.clean_wage_industry, b, raw_dir),
    }

    # ---- benchmark: national + region series ------------------------------
    if u_reg is None:
        log.error("primary unemployed table unavailable; dashboard cannot compute KPIs")
        return b
    periods = _periods_frame(u_reg)
    u_nat = _by_period(u_reg, "value_k").rename("u_k")
    nat = periods.set_index("period_idx").join(u_nat)

    reg = u_reg.groupby(PERIOD_COLS + ["region", "region_basis"], as_index=False)["value_k"].sum().rename(columns={"value_k": "u_k"})
    if lf_os is not None:
        lf_reg = lf_os.groupby(["period_idx", "region"], as_index=False)["value_k"].sum().rename(columns={"value_k": "lf_k"})
        reg = reg.merge(lf_reg, on=["period_idx", "region"], how="left", validate="one_to_one")
        nat = nat.join(_by_period(lf_os, "value_k").rename("lf_k"))
        # cross-check the denominator against the second, independent LF table
        if lf_rs is not None:
            issues, lf_failed = v.reconcile(_by_period(lf_os, "value_k"), _by_period(lf_rs, "value_k"), "labour_force",
                                            "กำลังแรงงานรวม: OS_02_0001_01 เทียบ LFS_02_20534_1", tol=0.005, abs_tol=5.0)
            b.report.add(issues)
        else:
            lf_failed = set()
    else:
        reg["lf_k"] = np.nan
        nat["lf_k"] = np.nan
        lf_failed = set()
    reg["rate_pct"] = np.where(reg["lf_k"] > 0, reg["u_k"] / reg["lf_k"] * 100, np.nan)
    reg.loc[reg["period_idx"].isin(list(lf_failed)), "rate_pct"] = np.nan  # conflicting denominators: no rate
    nat["rate_calc_pct"] = np.where(nat["lf_k"] > 0, nat["u_k"] / nat["lf_k"] * 100, np.nan)

    # published national rate: newest table first, older table fills earlier years
    def _nat(rt):
        if rt is None:
            return pd.Series(dtype=float)
        m = (rt["region"] == "ทั่วประเทศ") & (rt["sex"] == "รวม") & (rt["age_group"] == "รวม") & (rt["area"] == "รวม")
        return rt[m].drop_duplicates("period_idx").set_index("period_idx")["rate_pct"]

    pub_new, pub_old = _nat(rate_new), _nat(rate_old)
    if len(pub_new) and len(pub_old):
        ov = pd.concat([pub_new.rename("new"), pub_old.rename("old")], axis=1).dropna()
        bad = ov[(ov["new"] - ov["old"]).abs() > config.RATE_TOL_PP]
        if len(bad):
            b.report.add(v.Issue("warning", "rate_tables_conflict", "rates",
                                 f"อัตราที่ สสช. เผยแพร่ 2 ตารางขัดแย้งกัน {len(bad)} ไตรมาส (ใช้ตารางใหม่) เช่น "
                                 + ", ".join(f"{nz.period_label(i // 4, i % 4 + 1)}: {r.old}→{r.new}" for i, r in bad.head(3).iterrows()),
                                 len(bad)))
    nat["rate_pub_pct"] = pub_new.combine_first(pub_old).reindex(nat.index)
    gap = (nat["rate_calc_pct"] - nat["rate_pub_pct"]).abs()
    nat["rate_gap_pp"] = gap
    nat["quality_ok"] = nat["rate_calc_pct"].notna() & ~(gap > config.RATE_TOL_PP) & ~nat.index.isin(list(lf_failed))
    note = pd.Series("", index=nat.index)
    note[nat["rate_calc_pct"].isna()] = "ไม่มีกำลังแรงงานของไตรมาสนี้"
    note[gap > config.RATE_TOL_PP] = "อัตราที่คำนวณต่างจากที่ สสช. เผยแพร่เกินความคลาดเคลื่อนจากการปัดเศษ"
    note[nat.index.isin(list(lf_failed))] = "กำลังแรงงานจาก 2 ตารางไม่ตรงกัน"
    nat["quality_note"] = note
    conf_rate = []
    lf_a, lf_b = (_by_period(lf_os, "value_k") if lf_os is not None else None), (_by_period(lf_rs, "value_k") if lf_rs is not None else None)
    for p in nat.index[~nat["quality_ok"] & nat["rate_calc_pct"].notna()]:
        if p in lf_failed and lf_a is not None and lf_b is not None and p in lf_a.index and p in lf_b.index:
            va, vb = float(lf_a[p]), float(lf_b[p])
            conf_rate.append({"period_idx": int(p), "values": {"กำลังแรงงานรวม ตาราง OS_02_0001_01": va, "กำลังแรงงานรวม ตาราง LFS_02_20534_1": vb},
                              "gap": abs(va / vb - 1) * 100 if vb else None, "unit": "พันคน", "gap_unit": "%",
                              "reason": "กำลังแรงงานรวมจาก 2 ตารางของ สสช. ไม่ตรงกัน (ตัวหารของอัตราไม่แน่นอน) จึงไม่แสดงอัตราการว่างงาน"})
        elif pd.notna(gap.get(p)) and gap[p] > config.RATE_TOL_PP:
            conf_rate.append({"period_idx": int(p), "values": {"อัตราที่คำนวณเอง (ผู้ว่างงาน ÷ กำลังแรงงาน)": float(nat.at[p, "rate_calc_pct"]),
                                                              "อัตราที่ สสช. ประกาศ": float(nat.at[p, "rate_pub_pct"])},
                              "gap": float(gap[p]), "unit": "%", "gap_unit": "จุด",
                              "reason": f"อัตราที่คำนวณต่างจากที่ สสช. ประกาศเกิน {config.RATE_TOL_PP} จุด"})
    b.availability.setdefault("conflicts", {})["rate"] = conf_rate
    # the rate shown on the dashboard exists only where the calculation is consistent
    nat["rate_pct"] = np.where(nat["quality_ok"], nat["rate_calc_pct"], np.nan)
    n_bad = int((~nat["quality_ok"] & nat["rate_calc_pct"].notna()).sum())
    if n_bad:
        labels = [nz.period_label(i // 4, i % 4 + 1) for i in nat.index[~nat["quality_ok"] & nat["rate_calc_pct"].notna()]]
        b.report.add(v.Issue("warning", "rate_consistency", "national",
                             f"อัตราการว่างงานที่คำนวณไม่สอดคล้องกับที่ สสช. เผยแพร่ {n_bad} ไตรมาส ({', '.join(labels[:6])}) — ทำเครื่องหมายไว้และไม่ใช้ในการวิเคราะห์สหสัมพันธ์", n_bad))
    nat = nat.reset_index()
    b.tables["national"] = nat
    b.tables["region_series"] = reg.sort_values(["period_idx", "region"]).reset_index(drop=True)
    if lf_os is not None:
        b.tables["lf_region_sex"] = lf_os.groupby(PERIOD_COLS + ["region", "sex"], as_index=False)["value_k"].sum()

    # ---- reconcile breakdowns against the benchmark --------------------------
    u_nat_s = u_nat
    if u_edu is not None:
        issues, failed = v.reconcile(_by_period(u_edu, "value_k"), u_nat_s, "nso_u_edu", "ผู้ว่างงานตามการศึกษา เทียบยอดรวมประเทศ")
        b.report.add(issues)
        b.excluded["nso_u_edu"] = sorted(failed)
        b.tables["u_edu"] = u_edu[~u_edu["period_idx"].isin(failed)].reset_index(drop=True)
    if u_age is not None:
        issues, failed = v.reconcile(_by_period(u_age, "value_k"), u_nat_s, "nso_u_age_status", "ผู้ว่างงานตามกลุ่มอายุ เทียบยอดรวมประเทศ")
        b.report.add(issues)
        b.excluded["nso_u_age_status"] = sorted(failed)
        b.tables["u_age"] = u_age[~u_age["period_idx"].isin(failed)].reset_index(drop=True)
    if cube is not None:
        issues, failed = v.reconcile(_by_period(cube, "value_k"), u_nat_s, "nso_u_cube", "ผู้ว่างงานตารางข้ามมิติ เทียบยอดรวมประเทศ")
        b.report.add(issues)
        failed = set(failed)
        cube_reg = cube.groupby(["period_idx", "region"])["value_k"].sum()
        bench_reg = reg.set_index(["period_idx", "region"])["u_k"]
        for r in cube_reg.index.get_level_values("region").unique():
            iss, f = v.reconcile(cube_reg.xs(r, level="region"), bench_reg.xs(r, level="region"), "nso_u_cube",
                                 f"ผู้ว่างงานภาค{r} ตารางข้ามมิติ เทียบตารางภาค", tol=0.02, abs_tol=0.3)
            failed |= f
            if f:
                b.report.add(iss)
        if "u_edu" in b.tables and len(b.tables["u_edu"]):
            ce = cube.groupby(["period_idx", "edu_group"])["value_k"].sum()
            be = b.tables["u_edu"].groupby(["period_idx", "edu_group"])["value_k"].sum()
            for g in be.index.get_level_values("edu_group").unique():
                iss, f = v.reconcile(ce.xs(g, level="edu_group") if g in ce.index.get_level_values("edu_group") else pd.Series(dtype=float),
                                     be.xs(g, level="edu_group"), "nso_u_cube", f"ผู้ว่างงานกลุ่ม {g}", tol=0.03, abs_tol=0.6)
                failed |= f
        b.excluded["nso_u_cube"] = sorted(failed)
        b.report.add(v.Issue("info", "reconciliation", "nso_u_cube",
                             f"ตารางข้ามมิติใช้ได้ {cube['period_idx'].nunique() - len(failed)} จาก {cube['period_idx'].nunique()} ไตรมาส "
                             f"(ไตรมาสที่ยอดย่อยไม่ตรงกับยอดรวมถูกยกเว้น)", len(failed)))
        b.tables["cube"] = cube[~cube["period_idx"].isin(failed)].reset_index(drop=True)
    if prov is not None:
        allp = prov[prov["sex"] == "รวม"]
        # province list may contain a national row; do not add it on top of the provinces
        names = allp["province"].unique()
        nat_rows = [n for n in names if n in nz.NATIONAL_LABELS or "ทั่ว" in str(n) or str(n) == "รวม"]
        if nat_rows:
            b.report.add(v.Issue("info", "double_counting", "nso_u_province", f"ตัดแถวรวมระดับประเทศ {nat_rows} ออกก่อนบวกจังหวัด (กันนับซ้ำ)"))
        prov = prov[~prov["province"].isin(nat_rows)].copy()
        allp = prov[prov["sex"] == "รวม"]
        issues, failed = v.reconcile(_by_period(allp.rename(columns={"unemployed_k": "value_k"}), "value_k"), u_nat_s, "nso_u_province",
                                     "ผู้ว่างงานรายจังหวัด (รวมจังหวัด) เทียบยอดรวมประเทศ", tol=0.03, abs_tol=2.0)
        b.report.add(issues)
        b.excluded["nso_u_province"] = sorted(failed)
        b.tables["province"] = prov[~prov["period_idx"].isin(failed)].reset_index(drop=True)
    if emp_edu is not None:
        b.tables["emp_edu"] = emp_edu
    pubs = []
    for df_, tag in ((rate_old, "nso_rate_old"), (rate_new, "nso_rate_new")):
        if df_ is not None:
            pubs.append(df_.assign(source=tag))
    if pubs:
        allr = pd.concat(pubs, ignore_index=True).sort_values("source", ascending=False)  # new before old
        b.tables["rates_pub"] = allr.drop_duplicates(["period_idx", "region", "area", "sex", "age_group"]).reset_index(drop=True)

    # ---- economic + factor tables ---------------------------------------------
    if prov_reg is not None and geo is not None:
        # the regions NSO assigns to provinces must be the same regions used in the regional unemployment table
        reg_by_year = b.tables["region_series"].groupby("year_be")["region"].agg(lambda s: set(s))
        ok_years = []
        for y, g in prov_reg.groupby("year_be"):
            if y in reg_by_year.index and set(g["region"]) != reg_by_year[y]:
                b.report.add(v.Issue("warning", "region_definition", "province_region",
                                     f"ปี {y}: ภาคในตารางจังหวัด {sorted(set(g['region']))} ไม่ตรงกับภาคในตารางผู้ว่างงานรายภาค — ไม่ใช้ทำแผนที่ปีนี้"))
            else:
                ok_years.append(y)
        prov_reg = prov_reg[prov_reg["year_be"].isin(ok_years)]
        if len(prov_reg):
            b.tables["province_region"] = prov_reg
            b.geo = geo
    if gdp is not None:
        b.tables["gdp"] = gdp
    if sso is not None:
        b.tables["sso"] = sso
    if bot is not None:
        b.tables["bot_reasons"] = bot

    lm.build(b, lm_tables)   # employment rate + average wage (checked across their independent tables)
    _load_headcount(b, emp_ref, raw_dir)   # employed persons by region x sex x age (NSO OS_02_0002_01), checked against NSO LFS_02_20535_1

    regions5.collapse(b)   # the same five regions in every period (see regions5.py)
    _write_processed(b)
    intro_payload.write(b)   # numbers + map for the intro film (never breaks the load)
    return b


def _load_headcount(b: DataBundle, emp_ref, raw_dir: Path | None = None) -> None:
    spec = config.SOURCES_BY_KEY["nso_emp_age_sex"]
    path = dl.raw_path(spec, raw_dir)
    if not path.exists():
        return
    try:
        raw = c.read_raw_csv(path)
        raw["quarter"] = raw["quarter"].astype(str).str.extract(r"(\d)")[0]      # "ไตรมาส 3" -> 3
        raw["area"] = np.nan                                                      # the table has no area split: every row is the all-areas figure
        raw["emp_headcount"] = raw["value"]
        df, rep = mf.clean_headcount(raw)
    except Exception as exc:
        log.exception("cannot read %s", path)
        b.report.add(v.Issue("warning", "read", mf.TABLE, f"อ่านตารางผู้มีงานทำตามกลุ่มอายุไม่ได้: {type(exc).__name__} — ไม่ใช้ตารางนี้"))
        b.availability[mf.TABLE] = {"ok": False, "rows": 0, "kind": "validation", "reason": "อ่านไฟล์ไม่ได้"}
        return
    b.report.extend(rep)
    if df.empty:
        b.availability[mf.TABLE] = {"ok": False, "rows": 0, "kind": "validation", "reason": "; ".join(i.message for i in rep.errors) or "ข้อมูลว่าง"}
        return
    df, rep2, unchecked = mf.reconcile_with_nso(df, emp_ref)
    b.report.extend(rep2)
    b.availability[mf.TABLE] = {"ok": len(df) > 0, "rows": len(df), "kind": "ok" if len(df) else "validation", "reason": None}
    if df.empty:
        return
    b.tables["lm_headcount"] = df
    nat = mf.national_employed(df)
    nat["checked_vs_nso"] = ~nat["period_idx"].isin(unchecked)
    b.tables["lm_employed_national"] = nat
    b.report.add(mf.plausibility(nat, b.get("national")))


def _write_processed(b: DataBundle) -> None:
    try:
        config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
        for name in ("national", "region_series", "gdp", "bot_reasons", "sso", "lm_national", "lm_region", "lm_sex_age", "lm_edu", "lm_industry", "lm_employed_national"):
            if b.has(name):
                b.tables[name].to_csv(config.DATA_PROCESSED / f"{name}.csv", index=False, encoding="utf-8-sig")
        b.report.to_frame().to_csv(config.DATA_PROCESSED / "validation_report.csv", index=False, encoding="utf-8-sig")
    except OSError:
        log.exception("cannot write processed files")
