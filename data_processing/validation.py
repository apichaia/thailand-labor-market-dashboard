"""Data validation. Checks *report* problems; they never edit the data.

Every check returns a list of ``Issue`` objects. A ``ValidationReport`` collects
them, writes them to the log and lets the pipeline decide what to exclude.
Severity:
    error   -> the table (or the affected periods) must not be used
    warning -> usable, but the user must be told
    info    -> informational
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

import config
from data_processing import normalize

log = logging.getLogger("validation")


@dataclass
class Issue:
    severity: str
    check: str
    table: str
    message: str
    count: int = 0
    details: dict = field(default_factory=dict)


@dataclass
class ValidationReport:
    issues: list[Issue] = field(default_factory=list)

    def add(self, issues) -> "ValidationReport":
        if isinstance(issues, Issue):
            issues = [issues]
        for i in issues:
            self.issues.append(i)
            level = {"error": logging.ERROR, "warning": logging.WARNING}.get(i.severity, logging.INFO)
            log.log(level, "[%s] %s: %s", i.table, i.check, i.message)
        return self

    def extend(self, other: "ValidationReport") -> "ValidationReport":
        self.issues.extend(other.issues)
        return self

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def for_table(self, table: str) -> list[Issue]:
        return [i for i in self.issues if i.table == table]

    def to_frame(self) -> pd.DataFrame:
        if not self.issues:
            return pd.DataFrame(columns=["severity", "check", "table", "message", "count"])
        return pd.DataFrame([{k: v for k, v in asdict(i).items() if k != "details"} for i in self.issues])


# ---------------------------------------------------------------------------
# individual checks
# ---------------------------------------------------------------------------


def check_required_columns(df: pd.DataFrame, required: list[str], table: str) -> list[Issue]:
    missing = [c for c in required if c not in df.columns]
    if missing:
        return [Issue("error", "schema", table, f"ไม่พบคอลัมน์ที่จำเป็น: {', '.join(missing)}", len(missing),
                      {"missing": missing, "found": list(df.columns)})]
    return []


def check_numeric(df: pd.DataFrame, cols: list[str], table: str) -> list[Issue]:
    """Report (not coerce) values that are not numeric."""
    out = []
    for c in cols:
        if c not in df.columns:
            continue
        bad = pd.to_numeric(df[c], errors="coerce").isna() & df[c].notna()
        if bad.any():
            out.append(Issue("error", "dtype", table, f"คอลัมน์ {c} มีค่าที่ไม่ใช่ตัวเลข {int(bad.sum())} แถว",
                             int(bad.sum()), {"examples": df.loc[bad, c].astype(str).head(5).tolist()}))
    return out


def check_missing(df: pd.DataFrame, cols: list[str], table: str) -> list[Issue]:
    out = []
    for c in cols:
        if c in df.columns and df[c].isna().any():
            n = int(df[c].isna().sum())
            out.append(Issue("warning", "missing", table, f"คอลัมน์ {c} มีค่าว่าง {n} แถว (ไม่ถูกเติมค่า)", n))
    return out


def check_duplicates(df: pd.DataFrame, keys: list[str], table: str) -> list[Issue]:
    keys = [k for k in keys if k in df.columns]
    if not keys:
        return []
    dup = df.duplicated(keys, keep=False)
    if dup.any():
        n = int(df.duplicated(keys).sum())
        return [Issue("error", "duplicates", table, f"พบแถวซ้ำตามคีย์ {keys} จำนวน {n} แถว", n,
                      {"examples": df.loc[dup, keys].head(5).to_dict("records")})]
    return []


def check_period_validity(df: pd.DataFrame, table: str, year_col: str = "year_be", quarter_col: str = "quarter",
                          min_year: int = config.MIN_BE, max_year: int = config.MAX_BE) -> list[Issue]:
    out = []
    if year_col in df.columns:
        y = pd.to_numeric(df[year_col], errors="coerce")
        bad = y.isna() | (y < min_year) | (y > max_year)
        if bad.any():
            out.append(Issue("error", "period", table, f"ปีอยู่นอกช่วงที่ถูกต้อง ({min_year}-{max_year}) {int(bad.sum())} แถว", int(bad.sum())))
    if quarter_col in df.columns:
        q = pd.to_numeric(df[quarter_col], errors="coerce")
        bad = q.isna() | ~q.isin([1, 2, 3, 4])
        if bad.any():
            out.append(Issue("error", "period", table, f"ไตรมาสไม่ถูกต้อง {int(bad.sum())} แถว", int(bad.sum())))
    return out


def check_negative(df: pd.DataFrame, col: str, table: str) -> list[Issue]:
    if col not in df.columns:
        return []
    neg = pd.to_numeric(df[col], errors="coerce") < 0
    if neg.any():
        return [Issue("error", "negative", table, f"พบค่าติดลบในคอลัมน์ {col} {int(neg.sum())} แถว", int(neg.sum()))]
    return []


def check_unit(df: pd.DataFrame, unit_col: str, expected: set[str] | str, table: str) -> list[Issue]:
    """Units must be present, single-valued and as expected (e.g. 'พันคน')."""
    expected = {expected} if isinstance(expected, str) else set(expected)
    if unit_col not in df.columns:
        return [Issue("error", "unit", table, "ไม่พบคอลัมน์หน่วย จึงยืนยันหน่วยของตัวเลขไม่ได้")]
    seen = set(df[unit_col].dropna().astype(str).str.strip().unique())
    if not seen:
        return [Issue("error", "unit", table, "คอลัมน์หน่วยว่างทั้งหมด")]
    unexpected = seen - expected
    if unexpected:
        return [Issue("error", "unit", table, f"หน่วยที่พบ {sorted(seen)} ไม่ตรงกับที่คาดไว้ {sorted(expected)}", len(unexpected),
                      {"seen": sorted(seen), "expected": sorted(expected)})]
    return []


def check_value_range(df: pd.DataFrame, col: str, table: str, lo: float, hi: float, unit_label: str) -> list[Issue]:
    """Flag implausible magnitudes (e.g. a 'percent' column holding 187)."""
    if col not in df.columns:
        return []
    v = pd.to_numeric(df[col], errors="coerce")
    bad = (v < lo) | (v > hi)
    if bad.any():
        return [Issue("warning", "range", table, f"พบค่า {int(bad.sum())} แถวนอกช่วงที่เป็นไปได้ของ {unit_label} [{lo}, {hi}] — แถวเหล่านี้ไม่ถูกนำไปใช้", int(bad.sum()),
                      {"examples": df.loc[bad].head(5).to_dict("records")})]
    return []


def check_double_counting(df: pd.DataFrame, dim_col: str, group_cols: list[str], table: str) -> list[Issue]:
    """A dimension must not contain both a 'รวม' row and its components in the same cell."""
    if dim_col not in df.columns:
        return []
    is_total = df[dim_col].map(normalize.is_total_label)
    if not is_total.any():
        return []
    g = df.assign(_t=is_total).groupby(group_cols, dropna=False)["_t"].agg(["any", "all"])
    mixed = g[g["any"] & ~g["all"]]
    if len(mixed):
        return [Issue("error", "double_counting", table,
                      f"มิติ {dim_col} มีทั้งแถว 'รวม' และแถวย่อยปนกันใน {len(mixed)} กลุ่ม — ห้ามนำมาบวกรวมกัน", len(mixed))]
    return []


def reconcile(parts: pd.Series, total: pd.Series, table: str, label: str, tol: float = config.RECONCILE_TOL,
              abs_tol: float = 0.15) -> tuple[list[Issue], set]:
    """Compare sums by period against an independently published total.

    ``parts`` and ``total`` are indexed by ``period_idx``. A period fails when
    |parts - total| > max(abs_tol, tol * total). Returns (issues, failed_periods).
    """
    j = pd.concat([parts.rename("parts"), total.rename("total")], axis=1)
    both = j.dropna()
    diff = (both["parts"] - both["total"]).abs()
    limit = np.maximum(abs_tol, tol * both["total"].abs())
    failed = set(both.index[diff > limit])
    only_parts = j["total"].isna().sum()
    issues = []
    if failed:
        examples = {int(i): (round(float(both.loc[i, "parts"]), 2), round(float(both.loc[i, "total"]), 2)) for i in sorted(failed)[:6]}
        issues.append(Issue(
            "warning", "reconciliation", table,
            f"{label}: ยอดรวมไม่ตรงกับตารางอ้างอิงใน {len(failed)} จาก {len(both)} ไตรมาส — ไตรมาสเหล่านี้ถูกยกเว้นเมื่อใช้ตารางนี้",
            len(failed), {"periods": sorted(int(i) for i in failed), "examples": examples}))
    if only_parts:
        issues.append(Issue("info", "reconciliation", table, f"{label}: {int(only_parts)} ไตรมาสไม่มีตารางอ้างอิงให้เทียบ", int(only_parts)))
    return issues, failed


def check_join_keys(left: pd.DataFrame, right: pd.DataFrame, keys: list[str], table: str) -> list[Issue]:
    """Keys must exist on both sides and be unique on each side before a join."""
    out = []
    for name, d in (("ซ้าย", left), ("ขวา", right)):
        miss = [k for k in keys if k not in d.columns]
        if miss:
            out.append(Issue("error", "join", table, f"ตาราง{name}ไม่มีคอลัมน์คีย์ {miss}"))
            return out
        if d.duplicated(keys).any():
            out.append(Issue("error", "join", table, f"คีย์ในตาราง{name}ไม่ซ้ำกันไม่ได้ (จะเกิดการนับซ้ำเมื่อ Join)", int(d.duplicated(keys).sum())))
    if out:
        return out
    lk = set(map(tuple, left[keys].to_numpy().tolist()))
    rk = set(map(tuple, right[keys].to_numpy().tolist()))
    if not (lk & rk):
        out.append(Issue("error", "join", table, "ไม่มีช่วงเวลาที่ตรงกันระหว่างสองชุดข้อมูล"))
    else:
        out.append(Issue("info", "join", table,
                         f"Join คีย์ {keys}: ตรงกัน {len(lk & rk)}, มีเฉพาะซ้าย {len(lk - rk)}, มีเฉพาะขวา {len(rk - lk)}",
                         len(lk & rk)))
    return out


def check_frequency_compat(freq_left: str, freq_right: str, table: str) -> list[Issue]:
    if freq_left != freq_right:
        return [Issue("error", "frequency", table, f"ความถี่ไม่ตรงกัน ({freq_left} vs {freq_right}) — ไม่ Join โดยตรง")]
    return []


def check_not_empty(df: pd.DataFrame, table: str) -> list[Issue]:
    if df is None or len(df) == 0:
        return [Issue("error", "empty", table, "ชุดข้อมูลว่างเปล่า")]
    return []


def check_all_labels_mapped(series: pd.Series, unmapped_value: str, table: str, what: str) -> list[Issue]:
    bad = series == unmapped_value
    if bad.any():
        return [Issue("error", "label_mapping", table, f"พบป้ายกำกับ{what}ที่จัดกลุ่มไม่ได้ {int(bad.sum())} แถว", int(bad.sum()))]
    return []
