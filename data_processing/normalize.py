"""Column / label / period normalisation.

Only *spelling variants of the same label* are unified here (for example
'2) กลาง' and 'ภาคกลาง'). Nothing is merged across different concepts.
"""
from __future__ import annotations

import re
from datetime import date

import pandas as pd

import config

TOTAL_LABELS = {"รวม", "ยอดรวม", "ทั้งหมด", "รวมยอด", "รวมทั้งหมด"}
NATIONAL_LABELS = {"ทั่วประเทศ", "ทั่วราชอาณาจักร"}

# --- columns -----------------------------------------------------------------

COLUMN_ALIASES = {
    "lavel_educational": "level_of_edu",  # sic: typo in NSO source tables
    "labor_force_sta": "labor_force_status",
}


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """lower-case, strip BOMs/spaces, unify known aliases (returns a copy)."""
    out = df.copy()
    cols = []
    for c in out.columns:
        name = str(c).replace("﻿", "").strip().lower()
        name = re.sub(r"[^0-9a-zA-Zก-๙]+", "_", name).strip("_")
        cols.append(COLUMN_ALIASES.get(name, name))
    out.columns = cols
    return out


# --- periods -----------------------------------------------------------------


def parse_quarter(value) -> int | None:
    """'ไตรมาส 1' / 'ไตรมาสที่ 3' / 'Q2' / 4 -> int 1..4, else None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    m = re.search(r"([1-4])", str(value))
    return int(m.group(1)) if m else None


def year_era(years: pd.Series) -> str:
    """Return 'BE', 'CE' or 'mixed' by inspecting actual values (never assume)."""
    y = pd.to_numeric(years, errors="coerce").dropna()
    if y.empty:
        return "unknown"
    be = ((y >= config.MIN_BE) & (y <= config.MAX_BE)).all()
    ce = ((y >= 1900) & (y <= 2200)).all()
    if be:
        return "BE"
    if ce:
        return "CE"
    return "mixed"


def be_to_ce(year: int) -> int:
    if not (config.MIN_BE <= int(year) <= config.MAX_BE):
        raise ValueError(f"{year} ไม่อยู่ในช่วงปี พ.ศ. ที่ถูกต้อง")
    return int(year) - config.BE_OFFSET


def ce_to_be(year: int) -> int:
    if not (1900 <= int(year) <= 2200):
        raise ValueError(f"{year} ไม่อยู่ในช่วงปี ค.ศ. ที่ถูกต้อง")
    return int(year) + config.BE_OFFSET


def add_period_columns(df: pd.DataFrame, year_col: str = "year", quarter_col: str = "quarter") -> pd.DataFrame:
    """Add year_be, quarter(int), period_idx, period_label and date (CE quarter start).

    The year column must already be verified as BE (see ``year_era``).
    """
    out = df.copy()
    out["year_be"] = pd.to_numeric(out[year_col], errors="coerce").astype("Int64")
    out["quarter_n"] = out[quarter_col].map(parse_quarter).astype("Int64")
    out = out.drop(columns=[c for c in (year_col, quarter_col) if c not in ("year_be",)], errors="ignore")
    out = out.rename(columns={"quarter_n": "quarter"})
    ok = out["year_be"].notna() & out["quarter"].notna()
    out = out[ok].copy()
    out["year_be"] = out["year_be"].astype(int)
    out["quarter"] = out["quarter"].astype(int)
    out["period_idx"] = out["year_be"] * 4 + out["quarter"] - 1
    out["period_label"] = "ไตรมาส " + out["quarter"].astype(str) + "/" + out["year_be"].astype(str)
    out["date"] = [pd.Timestamp(date(y - config.BE_OFFSET, 3 * (q - 1) + 1, 1)) for y, q in zip(out["year_be"], out["quarter"])]
    return out


def period_label(year_be: int, quarter: int) -> str:
    return f"ไตรมาส {quarter}/{year_be}"


def period_months_th(quarter: int) -> str:
    return {1: "ม.ค.–มี.ค.", 2: "เม.ย.–มิ.ย.", 3: "ก.ค.–ก.ย.", 4: "ต.ค.–ธ.ค."}[quarter]


# --- labels ------------------------------------------------------------------

_NUM_PREFIX = re.compile(r"^\s*\d+\s*[\.\)]\s*")
_SHORT_REGIONS = {"กลาง", "เหนือ", "ใต้", "ใต้ชายแดน", "ตะวันออก", "ตะวันออกเฉียงเหนือ"}


def clean_label(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).replace("\xa0", " ").strip()
    s = _NUM_PREFIX.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_region(value) -> str | None:
    s = clean_label(value)
    if s is None:
        return None
    if s in NATIONAL_LABELS:
        return "ทั่วประเทศ"
    if s in _SHORT_REGIONS:
        return "ภาค" + s
    return s


def normalize_sex(value) -> str | None:
    s = clean_label(value)
    if s is None:
        return None
    return "รวม" if s in TOTAL_LABELS else s


def normalize_area(value) -> str | None:
    s = clean_label(value)
    if s is None:
        return None
    if s in TOTAL_LABELS:
        return "รวม"
    if s in ("เขตเทศบาล", "ในเขตเทศบาล"):
        return "ในเขตเทศบาล"
    return s


def normalize_age_group(value) -> str | None:
    s = clean_label(value)
    if s is None:
        return None
    if s in TOTAL_LABELS:
        return "รวม"
    s = re.sub(r"\s*-\s*", "-", s)
    if s.startswith("60"):
        return "60 ปีขึ้นไป"
    return s


EDU_ORDER = [
    "ต่ำกว่าประถมศึกษา (รวมไม่มีการศึกษา)",
    "ประถมศึกษา",
    "มัธยมศึกษาตอนต้น",
    "มัธยมศึกษาตอนปลาย (ทุกสาย)",
    "อุดมศึกษา (ทุกสาย)",
    "อื่น ๆ / ไม่ทราบ",
]
EDU_UNMAPPED = "ไม่สามารถจัดกลุ่ม"


def normalize_education_group(value) -> str | None:
    """Map a raw education label to one of six coarse groups.

    Fine-grained labels were renamed between survey years (for example
    'สายวิชาการ' vs 'สายวิชาการศึกษา'), so only the unambiguous level is kept.
    Totals return None. Unknown labels return EDU_UNMAPPED (and are reported).
    """
    s = clean_label(value)
    if s is None or s in TOTAL_LABELS:
        return None
    if s in ("ไม่มีการศึกษา",) or s.startswith("ต่ำกว่าประถม"):
        return EDU_ORDER[0]
    if s == "ประถมศึกษา":
        return EDU_ORDER[1]
    if s.startswith("มัธยมศึกษาตอนต้น"):
        return EDU_ORDER[2]
    if s.startswith("มัธยมศึกษาตอนปลาย"):
        return EDU_ORDER[3]
    if s.startswith("อุดมศึกษา"):
        return EDU_ORDER[4]
    if s.startswith("อื่น") or s.startswith("การศึกษาอื่น") or s in ("ไม่ทราบ", "99"):
        return EDU_ORDER[5]
    return EDU_UNMAPPED


def is_total_label(value) -> bool:
    s = clean_label(value)
    return s is not None and s in TOTAL_LABELS
