"""Per-table cleaners: raw frame -> (tidy frame, ValidationReport).

Cleaners never edit the raw file. They validate first, then reshape. A table
that fails a blocking check is returned as an empty frame together with an
``error`` issue, so downstream code cannot compute from it by accident.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

import config
from data_processing.province_codes import NAME_ALIASES, PROVINCE_CODES
from data_processing import normalize as nz
from data_processing import validation as v

THOUSAND = "พันคน"
EMPTY = pd.DataFrame()


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------


def read_raw_csv(path: Path, encoding: str = "utf-8-sig") -> pd.DataFrame:
    """Read a raw CSV (Thai encodings supported). Values are not altered."""
    raw = Path(path).read_bytes()
    text = raw.decode(encoding)
    return pd.read_csv(io.StringIO(text.lstrip("﻿")), dtype=str, keep_default_na=True)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    return nz.normalize_column_names(df)


def validate_raw_data(df: pd.DataFrame, *, table: str, required: list[str], keys: list[str] | None = None,
                      unit: set[str] | str | None = None, value_col: str = "value") -> v.ValidationReport:
    """Generic raw-schema validation used by every NSO table."""
    rep = v.ValidationReport()
    rep.add(v.check_not_empty(df, table))
    if not rep.ok:
        return rep
    rep.add(v.check_required_columns(df, required, table))
    if not rep.ok:
        return rep
    rep.add(v.check_numeric(df, [value_col], table))
    if unit is not None:
        rep.add(v.check_unit(df, "unit", unit, table))
    return rep


def _fail(rep: v.ValidationReport) -> tuple[pd.DataFrame, v.ValidationReport]:
    return EMPTY.copy(), rep


def _finish(df: pd.DataFrame, rep: v.ValidationReport, table: str, keys: list[str], value_col: str = "value_k",
            allow_negative: bool = False) -> tuple[pd.DataFrame, v.ValidationReport]:
    rep.add(v.check_period_validity(df, table))
    rep.add(v.check_duplicates(df, keys, table))
    if not allow_negative:
        rep.add(v.check_negative(df, value_col, table))
    rep.add(v.check_missing(df, [value_col], table))
    if not rep.ok:
        return _fail(rep)
    return df.reset_index(drop=True), rep


def _prep(raw: pd.DataFrame, table: str, required: list[str], unit, value_col="value"):
    df = normalize_column_names(raw)
    rep = validate_raw_data(df, table=table, required=required, unit=unit, value_col=value_col)
    if not rep.ok:
        return None, rep
    era = nz.year_era(df["year"])
    if era != "BE":
        rep.add(v.Issue("error", "year_era", table, f"ปีในไฟล์ไม่ใช่ พ.ศ. ทั้งหมด (ตรวจพบ: {era}) — ไม่แปลงปีโดยอัตโนมัติ"))
        return None, rep
    return df, rep


# ---------------------------------------------------------------------------
# unemployed counts
# ---------------------------------------------------------------------------


def clean_u_region(raw: pd.DataFrame, table: str = "nso_u_region"):
    df, rep = _prep(raw, table, ["year", "quarter", "region", "area", "value", "unit"], THOUSAND)
    if df is None:
        return _fail(rep)
    df = nz.add_period_columns(df)
    df["region"] = df["region"].map(nz.normalize_region)
    df["area"] = df["area"].map(nz.normalize_area)
    df["value_k"] = pd.to_numeric(df["value"], errors="coerce")
    rep.add(v.check_double_counting(df, "area", ["period_idx", "region"], table))
    rep.add(v.check_double_counting(df, "region", ["period_idx"], table))
    df = df[["year_be", "quarter", "period_idx", "period_label", "date", "region", "area", "value_k"]]
    df = _add_region_basis(df)
    return _finish(df, rep, table, ["period_idx", "region", "area"])


def _add_region_basis(df: pd.DataFrame) -> pd.DataFrame:
    """NSO changed the regional breakdown from 5 to 7 groups in 2568."""
    seven = df.groupby("period_idx")["region"].transform(lambda s: "ภาคตะวันออก" in set(s))
    df["region_basis"] = np.where(seven, "7 ภาค", "5 ภาค")
    return df


def clean_u_cube(raw: pd.DataFrame, table: str = "nso_u_cube"):
    df, rep = _prep(raw, table, ["year", "quarter", "region", "sex", "level_of_edu", "dur_seek_job", "value", "unit"], THOUSAND)
    if df is None:
        return _fail(rep)
    df = nz.add_period_columns(df)
    df["region"] = df["region"].map(nz.normalize_region)
    df["sex"] = df["sex"].map(nz.normalize_sex)
    df["edu_raw"] = df["level_of_edu"].map(nz.clean_label)
    df["edu_group"] = df["level_of_edu"].map(nz.normalize_education_group)
    df["duration"] = df["dur_seek_job"].map(nz.clean_label)
    df["value_k"] = pd.to_numeric(df["value"], errors="coerce")
    rep.add(v.check_double_counting(df, "sex", ["period_idx", "region"], table))
    rep.add(v.check_double_counting(df, "level_of_edu", ["period_idx", "region", "sex"], table))
    rep.add(v.check_all_labels_mapped(df["edu_group"].fillna(""), nz.EDU_UNMAPPED, table, "ระดับการศึกษา"))
    df = df[["year_be", "quarter", "period_idx", "period_label", "date", "region", "sex", "edu_raw", "edu_group", "duration", "value_k"]]
    df = _add_region_basis(df)
    return _finish(df, rep, table, ["period_idx", "region", "sex", "edu_raw", "duration"])


def clean_u_edu(raw: pd.DataFrame, table: str = "nso_u_edu"):
    df, rep = _prep(raw, table, ["year", "quarter", "level_of_edu", "value", "unit"], THOUSAND)
    if df is None:
        return _fail(rep)
    df = nz.add_period_columns(df)
    df["edu_raw"] = df["level_of_edu"].map(nz.clean_label)
    df["edu_group"] = df["level_of_edu"].map(nz.normalize_education_group)
    df["value_k"] = pd.to_numeric(df["value"], errors="coerce")
    rep.add(v.check_all_labels_mapped(df["edu_group"].fillna(""), nz.EDU_UNMAPPED, table, "ระดับการศึกษา"))
    rep.add(v.check_double_counting(df, "level_of_edu", ["period_idx"], table))
    df = df[["year_be", "quarter", "period_idx", "period_label", "date", "edu_raw", "edu_group", "value_k"]]
    return _finish(df, rep, table, ["period_idx", "edu_raw"])


def clean_u_age(raw: pd.DataFrame, table: str = "nso_u_age_status"):
    df, rep = _prep(raw, table, ["year", "quarter", "region", "age_group", "labor_force_status", "value", "unit"], THOUSAND)
    if df is None:
        return _fail(rep)
    df = nz.add_period_columns(df)
    df["region"] = df["region"].map(nz.normalize_region)
    df["age_group"] = df["age_group"].map(nz.normalize_age_group)
    df["status"] = df["labor_force_status"].map(nz.clean_label)
    df["value_k"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[["year_be", "quarter", "period_idx", "period_label", "date", "region", "age_group", "status", "value_k"]]
    # This source has quarters with missing region/age cells (zero cells omitted?).
    # We do not fill them; the pipeline only uses quarters that reconcile.
    return _finish(df, rep, table, ["period_idx", "region", "age_group", "status"])


def clean_u_province(raw: pd.DataFrame, table: str = "nso_u_province"):
    df = normalize_column_names(raw)
    rep = v.ValidationReport()
    rep.add(v.check_not_empty(df, table))
    rep.add(v.check_required_columns(df, ["year", "quarter", "province", "sex", "variable", "value", "unit"], table))
    if not rep.ok:
        return _fail(rep)
    rep.add(v.check_numeric(df, ["value"], table))
    if nz.year_era(df["year"]) != "BE":
        rep.add(v.Issue("error", "year_era", table, "ปีไม่ใช่ พ.ศ."))
        return _fail(rep)
    df = nz.add_period_columns(df)
    df["sex"] = df["sex"].map(nz.normalize_sex)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["variable"] = df["variable"].map(nz.clean_label)
    # each variable must carry its own, single unit
    for var, unit in (("ผู้ว่างงาน", "คน"), ("อัตราการว่างงาน", "ร้อยละ")):
        sub = df[df["variable"] == var]
        rep.add(v.check_unit(sub, "unit", unit, table))
    if not rep.ok:
        return _fail(rep)
    u = df[df["variable"] == "ผู้ว่างงาน"].rename(columns={"value": "unemployed_persons"})
    r = df[df["variable"] == "อัตราการว่างงาน"].rename(columns={"value": "rate_pct"})
    keys = ["period_idx", "province", "sex"]
    rep.add(v.check_duplicates(u, keys, table + ":unemployed"))
    rep.add(v.check_duplicates(r, keys, table + ":rate"))
    if not rep.ok:
        return _fail(rep)
    base = ["year_be", "quarter", "period_idx", "period_label", "date", "province", "sex"]
    out = u[base + ["unemployed_persons"]].merge(r[keys + ["rate_pct"]], on=keys, how="outer", validate="one_to_one")
    out["unemployed_k"] = out["unemployed_persons"] / 1000.0  # คน -> พันคน (explicit unit conversion)
    return _finish(out, rep, table, keys, value_col="unemployed_persons")


# ---------------------------------------------------------------------------
# labour force / employed (denominators)
# ---------------------------------------------------------------------------


def _clean_simple_k(raw, table, extra_cols, label_maps, keys):
    required = ["year", "quarter", "value", "unit"] + extra_cols
    df, rep = _prep(raw, table, required, THOUSAND)
    if df is None:
        return _fail(rep)
    df = nz.add_period_columns(df)
    for col, fn in label_maps.items():
        df[col] = df[col].map(fn)
    df["value_k"] = pd.to_numeric(df["value"], errors="coerce")
    keep = ["year_be", "quarter", "period_idx", "period_label", "date"] + list(label_maps) + ["value_k"]
    extra = [c for c in df.columns if c in ("edu_group",) and c not in keep]
    return df[keep + extra], rep


def clean_lf_region_area_sex(raw: pd.DataFrame, table: str = "nso_lf_region_area_sex"):
    df, rep = _clean_simple_k(raw, table, ["region", "area", "sex"],
                              {"region": nz.normalize_region, "area": nz.normalize_area, "sex": nz.normalize_sex},
                              ["period_idx", "region", "area", "sex"])
    if df is None or df.empty:
        return _fail(rep)
    return _finish(df, rep, table, ["period_idx", "region", "area", "sex"])


def clean_lf_region_sex(raw: pd.DataFrame, table: str = "nso_lf_region_sex"):
    df, rep = _clean_simple_k(raw, table, ["region", "sex"],
                              {"region": nz.normalize_region, "sex": nz.normalize_sex}, ["period_idx", "region", "sex"])
    if df is None or df.empty:
        return _fail(rep)
    return _finish(df, rep, table, ["period_idx", "region", "sex"])


def clean_emp_region_sex(raw: pd.DataFrame, table: str = "nso_emp_region_sex"):
    return clean_lf_region_sex(raw, table)


def clean_emp_region_sex_edu(raw: pd.DataFrame, table: str = "nso_emp_region_sex_edu"):
    df, rep = _prep(raw, table, ["year", "quarter", "region", "sex", "level_of_edu", "value", "unit"], THOUSAND)
    if df is None:
        return _fail(rep)
    df = nz.add_period_columns(df)
    df["region"] = df["region"].map(nz.normalize_region)
    df["sex"] = df["sex"].map(nz.normalize_sex)
    df["edu_raw"] = df["level_of_edu"].map(nz.clean_label)
    df["edu_group"] = df["level_of_edu"].map(nz.normalize_education_group)
    df["value_k"] = pd.to_numeric(df["value"], errors="coerce")
    rep.add(v.check_all_labels_mapped(df["edu_group"].fillna(""), nz.EDU_UNMAPPED, table, "ระดับการศึกษา"))
    df = df[["year_be", "quarter", "period_idx", "period_label", "date", "region", "sex", "edu_raw", "edu_group", "value_k"]]
    return _finish(df, rep, table, ["period_idx", "region", "sex", "edu_raw"])


# ---------------------------------------------------------------------------
# published rates (used to verify our own calculation, and for age groups)
# ---------------------------------------------------------------------------


def clean_rates(raw: pd.DataFrame, table: str):
    """NSO-published unemployment rate (percent). Rows with an implausible
    magnitude or a non-percent unit are dropped *and reported*."""
    df = normalize_column_names(raw)
    rep = v.ValidationReport()
    rep.add(v.check_not_empty(df, table))
    rep.add(v.check_required_columns(df, ["year", "quarter", "region", "sex", "age_group", "value"], table))
    if not rep.ok:
        return _fail(rep)
    rep.add(v.check_numeric(df, ["value"], table))
    if nz.year_era(df["year"]) != "BE":
        rep.add(v.Issue("error", "year_era", table, "ปีไม่ใช่ พ.ศ."))
        return _fail(rep)
    if "area" not in df.columns:
        df["area"] = "รวม"
    df = nz.add_period_columns(df)
    df["region"] = df["region"].map(nz.normalize_region)
    df["area"] = df["area"].map(nz.normalize_area)
    df["sex"] = df["sex"].map(nz.normalize_sex)
    df["age_group"] = df["age_group"].map(nz.normalize_age_group)
    df["rate_pct"] = pd.to_numeric(df["value"], errors="coerce")
    if "unit" in df.columns:
        non_pct = df["unit"].notna() & (df["unit"].astype(str).str.strip() != "ร้อยละ")
        if non_pct.any():
            rep.add(v.Issue("warning", "unit", table, f"พบหน่วยที่ไม่ใช่ร้อยละ {int(non_pct.sum())} แถว — ไม่นำมาใช้", int(non_pct.sum())))
            df = df[~non_pct]
    rep.add(v.check_value_range(df, "rate_pct", table, 0, 100, "ร้อยละ"))
    df = df[(df["rate_pct"] >= 0) & (df["rate_pct"] <= 100)]
    df = df[["year_be", "quarter", "period_idx", "period_label", "date", "region", "area", "sex", "age_group", "rate_pct"]]
    dup_cols = ["period_idx", "region", "area", "sex", "age_group"]
    rep.add(v.check_duplicates(df, dup_cols, table))
    if not rep.ok:
        return _fail(rep)
    return df.reset_index(drop=True), rep


# ---------------------------------------------------------------------------
# GDP (NESDC)
# ---------------------------------------------------------------------------


def _parse_nesdc_sheet(path: Path, sheet: str, value_header_contains: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
    header_row = None
    for i in range(min(12, len(raw))):
        if any(isinstance(c, str) and c.strip().lower().startswith(value_header_contains.lower()) for c in raw.iloc[i]):
            header_row = i
            break
    if header_row is None:
        raise ValueError(f"ไม่พบคอลัมน์ '{value_header_contains}' ในชีต {sheet}")
    col = next(j for j, c in enumerate(raw.iloc[header_row]) if isinstance(c, str) and c.strip().lower().startswith(value_header_contains.lower()))
    rows, year = [], None
    for i in range(header_row + 1, len(raw)):
        label = raw.iat[i, 0]
        if label is None or (isinstance(label, float) and np.isnan(label)):
            continue
        s = str(label).strip()
        m_year = re.match(r"^(\d{4})([a-zA-Z0-9]*)$", s)
        m_q = re.match(r"^Q([1-4])([a-zA-Z]*)$", s)
        if m_year:
            year = int(m_year.group(1))
        elif m_q and year is not None:
            val = pd.to_numeric(raw.iat[i, col], errors="coerce")
            rows.append({"year": year, "quarter": int(m_q.group(1)), "value": val, "flag": m_q.group(2) or None})
    return pd.DataFrame(rows)


def clean_gdp(path: Path, table: str = "nesdc_gdp"):
    """Return quarterly GDP growth (YoY %, original series) and CVM level."""
    rep = v.ValidationReport()
    try:
        yoy = _parse_nesdc_sheet(path, "Table 2.1", "Gross domestic product (CVM)")
        lvl = _parse_nesdc_sheet(path, "Table 2", "Gross domestic product (CVM)")
    except Exception as exc:  # parse failure = schema problem, not network
        rep.add(v.Issue("error", "schema", table, f"อ่านไฟล์ GDP ไม่ได้: {exc}"))
        return _fail(rep)
    for name, d in (("เทียบปีก่อน", yoy), ("ระดับ", lvl)):
        if d.empty:
            rep.add(v.Issue("error", "empty", table, f"ไม่พบข้อมูลรายไตรมาสของ GDP ({name})"))
    if not rep.ok:
        return _fail(rep)
    era = nz.year_era(yoy["year"])
    if era != "CE":
        rep.add(v.Issue("error", "year_era", table, f"ไฟล์ GDP คาดว่าเป็น ค.ศ. แต่ตรวจพบ {era}"))
        return _fail(rep)
    df = yoy.rename(columns={"value": "gdp_yoy_pct"}).merge(
        lvl.rename(columns={"value": "gdp_cvm_mbaht", "flag": "flag_level"}), on=["year", "quarter"], how="outer", validate="one_to_one")
    df = df.rename(columns={"year": "year_ce"})
    df["year_be"] = df["year_ce"] + config.BE_OFFSET
    df["period_idx"] = df["year_be"] * 4 + df["quarter"] - 1
    df["period_label"] = "ไตรมาส " + df["quarter"].astype(str) + "/" + df["year_be"].astype(str)
    df["date"] = [pd.Timestamp(int(y), 3 * (q - 1) + 1, 1) for y, q in zip(df["year_ce"], df["quarter"])]
    df = df.sort_values("period_idx").reset_index(drop=True)
    rep.add(v.check_duplicates(df, ["period_idx"], table))
    # cross-check published YoY against growth recomputed from the CVM levels
    lv = df.set_index("period_idx")["gdp_cvm_mbaht"]
    recomputed = pd.Series((lv.to_numpy() / lv.reindex(lv.index - 4).to_numpy() - 1) * 100, index=lv.index)
    diff = (recomputed - df.set_index("period_idx")["gdp_yoy_pct"]).abs().dropna()
    bad = diff[diff > 0.15]
    if len(bad):
        rep.add(v.Issue("warning", "gdp_yoy_check", table,
                        f"เทียบปีก่อน ที่เผยแพร่ต่างจากที่คำนวณจากระดับ ปริมาณลูกโซ่ เกิน 0.15 จุด {len(bad)} ไตรมาส (ใช้ค่า เทียบปีก่อน ตามที่ สศช. เผยแพร่)", len(bad)))
    else:
        rep.add(v.Issue("info", "gdp_yoy_check", table, f"เทียบปีก่อน ที่เผยแพร่ตรงกับที่คำนวณจากระดับ ปริมาณลูกโซ่ ({len(diff)} ไตรมาส)", len(diff)))
    rep.add(v.check_value_range(df, "gdp_yoy_pct", table, -40, 40, "ร้อยละ เทียบปีก่อน"))
    rep.add(v.check_missing(df, ["gdp_yoy_pct"], table))
    df = df.drop(columns=["flag_level"], errors="ignore").rename(columns={"flag": "gdp_flag"})
    return df[["year_ce", "year_be", "quarter", "period_idx", "period_label", "date", "gdp_yoy_pct", "gdp_cvm_mbaht", "gdp_flag"]], rep


# ---------------------------------------------------------------------------
# SSO benefit claims (proxy)
# ---------------------------------------------------------------------------


def clean_sso(path: Path, table: str = "sso_benefit"):
    rep = v.ValidationReport()
    try:
        text = Path(path).read_bytes().decode("cp874")
    except UnicodeDecodeError:
        rep.add(v.Issue("error", "encoding", table, "ถอดรหัสไฟล์ สำนักงานประกันสังคม (TIS-620/cp874) ไม่ได้"))
        return _fail(rep)
    rows = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3 and re.fullmatch(r"\d{4}", parts[0]):
            num = re.sub(r"[^\d]", "", parts[2])
            rows.append({"year_be": int(parts[0]), "reason": parts[1], "cases": int(num) if num else np.nan})
    df = pd.DataFrame(rows)
    rep.add(v.check_not_empty(df, table))
    if not rep.ok:
        return _fail(rep)
    if nz.year_era(df["year_be"]) != "BE":
        rep.add(v.Issue("error", "year_era", table, "ปีไม่ใช่ พ.ศ."))
        return _fail(rep)
    rep.add(v.check_duplicates(df, ["year_be", "reason"], table))
    rep.add(v.check_negative(df, "cases", table))
    rep.add(v.check_missing(df, ["cases"], table))
    if not rep.ok:
        return _fail(rep)
    return df, rep


# ---------------------------------------------------------------------------
# BOT reasons for leaving the previous job
# ---------------------------------------------------------------------------

BOT_TOTAL = "ผู้ว่างงานที่เคยทำงาน"


def clean_bot_reasons(path: Path, table: str = "bot_reasons"):
    rep = v.ValidationReport()
    html = Path(path).read_bytes().decode("utf-8", "replace")
    soup = BeautifulSoup(html, "html.parser")
    target = None
    for t in soup.find_all("table"):
        rows = t.find_all("tr")
        if len(rows) >= 8 and "ลาออก" in t.get_text():
            target = rows
            break
    if target is None:
        rep.add(v.Issue("error", "schema", table, "ไม่พบตารางเหตุผลที่ออกจากงานในหน้า ธปท."))
        return _fail(rep)
    header = [c.get_text(" ", strip=True) for c in target[0].find_all(["td", "th"])]
    periods = {}
    for j, h in enumerate(header):
        m = re.match(r"Q([1-4])/(\d{4})", h)
        if m:
            periods[j] = (int(m.group(2)), int(m.group(1)), "p" in h.split()[-1:] )
    if not periods:
        rep.add(v.Issue("error", "schema", table, "ไม่พบหัวคอลัมน์ไตรมาสในตาราง ธปท."))
        return _fail(rep)
    recs = []
    for tr in target[1:]:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < len(header) or not cells[1]:
            continue
        for j, (y, q, prelim) in periods.items():
            val = pd.to_numeric(cells[j].replace(",", ""), errors="coerce")
            recs.append({"year_be": y, "quarter": q, "category": cells[1], "value_k": val, "preliminary": prelim})
    df = pd.DataFrame(recs)
    if nz.year_era(df["year_be"]) != "BE":
        rep.add(v.Issue("error", "year_era", table, "ปีไม่ใช่ พ.ศ."))
        return _fail(rep)
    df["period_idx"] = df["year_be"] * 4 + df["quarter"] - 1
    df["period_label"] = "ไตรมาส " + df["quarter"].astype(str) + "/" + df["year_be"].astype(str)
    df["date"] = [pd.Timestamp(y - config.BE_OFFSET, 3 * (q - 1) + 1, 1) for y, q in zip(df["year_be"], df["quarter"])]
    rep.add(v.check_duplicates(df, ["period_idx", "category"], table))
    rep.add(v.check_negative(df, "value_k", table))
    # the seven reasons must add up to the published total of previously employed unemployed
    total = df[df["category"] == BOT_TOTAL].set_index("period_idx")["value_k"]
    parts = df[df["category"] != BOT_TOTAL].groupby("period_idx")["value_k"].sum()
    issues, failed = v.reconcile(parts, total, table, "ผลรวมเหตุผล 7 ข้อ เทียบ 'ผู้ว่างงานที่เคยทำงาน'", abs_tol=0.1)
    rep.add(issues)
    if not rep.ok:
        return _fail(rep)
    df["reconciled"] = ~df["period_idx"].isin(failed)
    return df.sort_values(["period_idx", "category"]).reset_index(drop=True), rep


# ---------------------------------------------------------------------------
# province -> region (as defined by NSO each year) and province geometry
# ---------------------------------------------------------------------------

THAI_NAME_TO_ISO = {v: k for k, v in PROVINCE_CODES.items()}


def clean_province_region(raw: pd.DataFrame, table: str = "nso_province_region"):
    """NSO's own province->region assignment per year (it changed from 5 to 7 regions in 2568).

    Only years that list exactly the 77 known provinces, each in exactly one region, are kept.
    """
    df = normalize_column_names(raw)
    rep = v.ValidationReport()
    rep.add(v.check_not_empty(df, table))
    rep.add(v.check_required_columns(df, ["year", "region", "province"], table))
    if not rep.ok:
        return _fail(rep)
    if nz.year_era(df["year"]) != "BE":
        rep.add(v.Issue("error", "year_era", table, "ปีไม่ใช่ พ.ศ."))
        return _fail(rep)
    df["year_be"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["province"] = df["province"].map(lambda x: NAME_ALIASES.get(str(x).strip(), str(x).strip()))
    df["region"] = df["region"].map(nz.normalize_region)
    out = df[["year_be", "region", "province"]].drop_duplicates().dropna()
    unknown = sorted(set(out["province"]) - set(THAI_NAME_TO_ISO))
    if unknown:
        rep.add(v.Issue("error", "label_mapping", table, f"พบชื่อจังหวัดที่ไม่อยู่ในรายการ 77 จังหวัด: {unknown[:5]}", len(unknown)))
        return _fail(rep)
    conflict = out.groupby(["year_be", "province"])["region"].nunique()
    if (conflict > 1).any():
        rep.add(v.Issue("error", "double_counting", table, "มีจังหวัดที่ถูกจัดอยู่ในหลายภาคในปีเดียวกัน — ไม่ใช้ตารางนี้", int((conflict > 1).sum())))
        return _fail(rep)
    counts = out.groupby("year_be")["province"].nunique()
    bad_years = counts[counts != len(THAI_NAME_TO_ISO)]
    if len(bad_years):
        rep.add(v.Issue("warning", "coverage", table, f"ปี {sorted(int(y) for y in bad_years.index)} มีจังหวัดไม่ครบ 77 จังหวัด จึงไม่ใช้ทำแผนที่", len(bad_years)))
        out = out[~out["year_be"].isin(bad_years.index)]
    if out.empty:
        rep.add(v.Issue("error", "empty", table, "ไม่มีปีใดที่นิยามจังหวัด→ภาคครบถ้วน"))
        return _fail(rep)
    out = out.assign(iso=out["province"].map(THAI_NAME_TO_ISO), year_be=out["year_be"].astype(int))
    return out.sort_values(["year_be", "province"]).reset_index(drop=True), rep


def _round_coords(obj, nd: int = 3):
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], (int, float)):
            return [round(float(x), nd) for x in obj]
        return [_round_coords(o, nd) for o in obj]
    return obj


def _ring_area(ring) -> float:
    """Signed area (shoelace) of a lon/lat ring: > 0 means counter-clockwise."""
    return 0.5 * sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]))


def _rewind_polygon(rings):
    """Exterior ring clockwise, holes counter-clockwise (the d3-geo convention used by Plotly).

    With the opposite winding (RFC 7946, counter-clockwise exterior) Plotly reads each province as
    'the whole globe except this shape' and fills the entire map. Only the vertex order changes.
    """
    out = []
    for i, ring in enumerate(rings):
        want_ccw = i != 0
        out.append(ring if (_ring_area(ring) > 0) == want_ccw else ring[::-1])
    return out


def _rewind_geometry(geom: dict) -> dict:
    if geom["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": _rewind_polygon(geom["coordinates"])}
    return {"type": "MultiPolygon", "coordinates": [_rewind_polygon(poly) for poly in geom["coordinates"]]}


def clean_geo(path: Path, table: str = "geo_provinces"):
    """Validate the province boundary file and keep a lean copy keyed by ISO code."""
    import json

    rep = v.ValidationReport()
    try:
        gj = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rep.add(v.Issue("error", "schema", table, "อ่านไฟล์ขอบเขตจังหวัดไม่ได้ (ไม่ใช่ GeoJSON)"))
        return _fail(rep)
    feats = gj.get("features") if isinstance(gj, dict) else None
    if gj.get("type") != "FeatureCollection" or not feats:
        rep.add(v.Issue("error", "schema", table, "ไฟล์ขอบเขตจังหวัดไม่ใช่ FeatureCollection"))
        return _fail(rep)
    isos = [(f.get("properties") or {}).get("shapeISO") for f in feats]
    if len(set(isos)) != len(isos):
        rep.add(v.Issue("error", "duplicates", table, "รหัสจังหวัดในไฟล์ขอบเขตซ้ำกัน"))
    missing, extra = sorted(set(PROVINCE_CODES) - set(isos)), sorted(set(isos) - set(PROVINCE_CODES))
    if missing or extra:
        rep.add(v.Issue("error", "join", table, f"รหัสจังหวัดในไฟล์ขอบเขตไม่ตรงกับรายการ 77 จังหวัด (ขาด {missing[:5]}, เกิน {extra[:5]})"))
    bad_geom = [i for i, f in zip(isos, feats) if (f.get("geometry") or {}).get("type") not in ("Polygon", "MultiPolygon")]
    if bad_geom:
        rep.add(v.Issue("error", "schema", table, f"รูปร่างบางจังหวัดไม่ใช่ Polygon: {bad_geom[:5]}"))
    if not rep.ok:
        return _fail(rep)
    lean = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": iso, "properties": {"iso": iso},
         "geometry": _rewind_geometry({"type": f["geometry"]["type"], "coordinates": _round_coords(f["geometry"]["coordinates"])})}
        for iso, f in zip(isos, feats)]}
    return lean, rep
