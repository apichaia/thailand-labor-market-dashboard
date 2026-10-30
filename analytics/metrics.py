"""KPI calculations. Pure functions: missing inputs give NaN, never zero."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from data_processing import normalize as nz
from data_processing import validation as v


def pct_change(new, old) -> float:
    """(new-old)/old*100; NaN when old is missing or zero."""
    try:
        if new is None or old is None or pd.isna(new) or pd.isna(old) or old == 0:
            return float("nan")
        return (float(new) - float(old)) / float(old) * 100.0
    except (TypeError, ValueError):
        return float("nan")


def unemployment_rate(unemployed, labor_force):
    """Unemployment rate (%) = unemployed / total labour force * 100.

    Works on scalars or Series. Labour force <= 0 or missing -> NaN.
    Both inputs must be in the same unit (e.g. thousand persons).
    """
    seq = (pd.Series, list, tuple, np.ndarray)
    scalar = not isinstance(unemployed, seq) and not isinstance(labor_force, seq)
    u = pd.to_numeric(pd.Series(unemployed) if isinstance(unemployed, seq) else pd.Series([unemployed]), errors="coerce")
    lf = pd.to_numeric(pd.Series(labor_force) if isinstance(labor_force, seq) else pd.Series([labor_force]), errors="coerce")
    out = u.astype(float) / lf.where(lf > 0).astype(float) * 100.0
    return float(out.iloc[0]) if scalar else out


def sum_by_period(df: pd.DataFrame, value_col: str, by: list[str], total_cols: list[str] | None = None) -> pd.DataFrame:
    """Sum ``value_col`` by ``by`` after refusing inputs that mix 'รวม' rows with components."""
    for c in total_cols or []:
        if c in df.columns and df[c].map(nz.is_total_label).any():
            raise ValueError(f"คอลัมน์ {c} มีแถว 'รวม' ปนอยู่ — การบวกรวมจะเกิดการนับซ้ำ")
    return df.groupby(by, as_index=False, dropna=False)[value_col].sum(min_count=1)


def add_changes(df: pd.DataFrame, value_col: str, idx_col: str = "period_idx") -> pd.DataFrame:
    """Add QoQ (lag 1 quarter) and YoY (lag 4 quarters) changes.

    The comparison period must exist exactly (idx-1 / idx-4); otherwise NaN.
    QoQ and YoY are separate columns and are never mixed.
    """
    out = df.sort_values(idx_col).copy()
    s = out.set_index(idx_col)[value_col]
    s = s[~s.index.duplicated()]
    for name, lag in (("qoq", 1), ("yoy", 4)):
        prev = s.reindex(s.index - lag)
        prev.index = s.index
        out[f"{name}_abs"] = out[idx_col].map(s - prev)
        out[f"{name}_pct"] = out[idx_col].map(((s - prev) / prev.where(prev != 0)) * 100.0)
    return out


def kpi_snapshot(series: pd.DataFrame, value_col: str, idx: int) -> dict:
    """Latest value plus QoQ/YoY at ``idx`` with a reason when not computable."""
    s = series.drop_duplicates("period_idx").set_index("period_idx")[value_col]
    cur = s.get(idx, np.nan)
    res = {"value": cur, "period_idx": idx}
    for name, lag, label in (("qoq", 1, "ไตรมาสก่อนหน้า"), ("yoy", 4, "ไตรมาสเดียวกันของปีก่อน")):
        prev = s.get(idx - lag, np.nan)
        res[f"{name}_prev"] = prev
        if pd.isna(cur):
            res[f"{name}_abs"] = res[f"{name}_pct"] = float("nan")
            res[f"{name}_reason"] = "ไม่มีข้อมูลของช่วงปัจจุบัน"
        elif pd.isna(prev):
            res[f"{name}_abs"] = res[f"{name}_pct"] = float("nan")
            res[f"{name}_reason"] = f"ไม่มีข้อมูล{label}สำหรับเทียบ"
        else:
            res[f"{name}_abs"] = float(cur - prev)
            res[f"{name}_pct"] = pct_change(cur, prev)
            res[f"{name}_reason"] = None
    return res


def detect_significant_changes(df: pd.DataFrame, col: str = "yoy_pct", z: float = 3.0) -> pd.DataFrame:
    """Flag periods whose YoY change is an outlier (robust z-score: median/MAD).

    YoY is used rather than QoQ because the raw quarterly series is not
    seasonally adjusted. This is a statistical flag, not an explanation.
    """
    out = df.copy()
    x = pd.to_numeric(out[col], errors="coerce")
    valid = x.dropna()
    if len(valid) < 8:
        out["robust_z"] = np.nan
        out["significant"] = False
        return out
    med = valid.median()
    mad = (valid - med).abs().median()
    if mad == 0:
        out["robust_z"] = np.nan
        out["significant"] = False
        return out
    out["robust_z"] = (x - med) / (1.4826 * mad)
    out["significant"] = out["robust_z"].abs() > z
    return out


# --- economic context --------------------------------------------------------


def merge_economic_indicators(unemp_q: pd.DataFrame, gdp_q: pd.DataFrame) -> tuple[pd.DataFrame, v.ValidationReport]:
    """Join quarterly unemployment with quarterly GDP growth on period_idx.

    Both inputs must be quarterly with a unique ``period_idx`` (BE-based; the GDP
    file is CE and was converted by year+543 after checking the era). Outer
    coverage differences are reported, and only matching quarters are returned.
    """
    rep = v.ValidationReport()
    rep.add(v.check_not_empty(unemp_q, "merge_economic"))
    rep.add(v.check_not_empty(gdp_q, "merge_economic"))
    if not rep.ok:
        return pd.DataFrame(), rep
    rep.add(v.check_join_keys(unemp_q, gdp_q, ["period_idx"], "merge_economic"))
    if not rep.ok:
        return pd.DataFrame(), rep
    gcols = [c for c in ("period_idx", "gdp_yoy_pct", "gdp_cvm_mbaht", "gdp_flag") if c in gdp_q.columns]
    merged = unemp_q.merge(gdp_q[gcols], on="period_idx", how="inner", validate="one_to_one")
    return merged.sort_values("period_idx").reset_index(drop=True), rep


def correlation_summary(x: pd.Series, y: pd.Series) -> dict:
    """Pearson r, Spearman rho, n and an approximate 95% CI (Fisher z)."""
    d = pd.concat([pd.to_numeric(x, errors="coerce"), pd.to_numeric(y, errors="coerce")], axis=1).dropna()
    n = len(d)
    if n < 8 or d.iloc[:, 0].std() == 0 or d.iloc[:, 1].std() == 0:
        return {"n": n, "pearson": float("nan"), "spearman": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"),
                "reason": "ข้อมูลไม่เพียงพอสำหรับคำนวณสหสัมพันธ์ (ต้องมีอย่างน้อย 8 ไตรมาส)"}
    r = float(d.iloc[:, 0].corr(d.iloc[:, 1]))
    rho = float(d.iloc[:, 0].rank().corr(d.iloc[:, 1].rank()))
    lo = hi = float("nan")
    if n > 3 and abs(r) < 1:
        z = math.atanh(r)
        se = 1 / math.sqrt(n - 3)
        lo, hi = math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)
    return {"n": n, "pearson": r, "spearman": rho, "ci_low": lo, "ci_high": hi, "reason": None}


def ols_line(x: pd.Series, y: pd.Series):
    """Least-squares line (slope, intercept) via numpy; None if not computable."""
    d = pd.concat([pd.to_numeric(x, errors="coerce"), pd.to_numeric(y, errors="coerce")], axis=1).dropna()
    if len(d) < 8 or d.iloc[:, 0].std() == 0:
        return None
    slope, intercept = np.polyfit(d.iloc[:, 0], d.iloc[:, 1], 1)
    return float(slope), float(intercept)
