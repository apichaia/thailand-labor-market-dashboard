"""The four summary cards follow the sidebar's years and quarters: several quarters give a properly weighted summary, one quarter gives that
quarter's own value. Pure functions only (no Streamlit), so every formula is easy to test.

* a rate is never an average of percentages: it is sum(numerator) / sum(denominator) over the quarters that have BOTH, with the same scope;
* the employment rate has no published population column, so the working-age population of a quarter is employed persons / (published rate / 100);
* wages have no employee counts to weight with, so they are a plain mean of the quarterly values and the card says so;
* a quarter with no checked value is left out (never a zero), and the card says how many of the selected quarters were usable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

import config


@dataclass
class Agg:
    value: float | None
    used: list[int] = field(default_factory=list)
    reason: str | None = None


def selected_quarters(f, latest: int) -> list[int]:
    """Quarters the sidebar selects (years x ticked quarters), from 2563 to the newest quarter that has data. No future quarters."""
    lo = max(config.SCOPE_START_BE * 4, (f.year_min or config.SCOPE_START_BE) * 4)
    hi = min(latest, (f.year_max * 4 + 3) if f.year_max else latest)
    return [i for i in range(lo, hi + 1) if (i % 4 + 1) in f.quarters]


def to_dict(df: pd.DataFrame | None, col: str) -> dict[int, float]:
    """{period_idx: value} with one value per quarter (first one wins) and no missing values."""
    if df is None or len(df) == 0 or col not in df.columns:
        return {}
    d = df.drop_duplicates("period_idx").dropna(subset=[col])
    return {int(p): float(v) for p, v in zip(d["period_idx"], d[col])}


def weighted_rate(num: dict[int, float], den: dict[int, float], qs: list[int]) -> Agg:
    """sum(num) / sum(den) x 100 over the selected quarters that have both a numerator and a positive denominator."""
    used = [q for q in qs if q in num and q in den and den[q] > 0]
    if not used:
        return Agg(None, [], "ไม่มีไตรมาสที่มีทั้งตัวตั้งและตัวหารตรงกัน")
    return Agg(sum(num[q] for q in used) / sum(den[q] for q in used) * 100.0, used)


def employment_rate(emp_m: dict[int, float], rate_pct: dict[int, float], qs: list[int]) -> Agg:
    """Weighted employment rate = sum(employed) / sum(working-age population) x 100, population = employed / (published rate / 100)."""
    pop = {q: emp_m[q] / (rate_pct[q] / 100.0) for q in emp_m if q in rate_pct and rate_pct[q] > 0}
    a = weighted_rate({q: emp_m[q] for q in pop}, pop, qs)
    if a.value is None:
        a.reason = "ข้อมูลไม่เพียงพอสำหรับคำนวณค่าเฉลี่ยช่วงนี้"
    return a


def unemployment_rate(unemployed: dict[int, float], labour_force: dict[int, float], rate_ok: dict[int, float], qs: list[int]) -> Agg:
    """Weighted unemployment rate = sum(unemployed) / sum(labour force) x 100, only over quarters whose rate passed the checks."""
    ok = [q for q in qs if q in rate_ok]
    a = weighted_rate(unemployed, labour_force, ok)
    if a.value is None:
        a.reason = "ข้อมูลไม่เพียงพอสำหรับคำนวณค่าเฉลี่ยช่วงนี้"
    return a


def simple_mean(vals: dict[int, float], qs: list[int]) -> Agg:
    used = [q for q in qs if q in vals]
    if not used:
        return Agg(None, [], "ไม่มีไตรมาสที่มีค่าที่ผ่านการตรวจสอบในช่วงที่เลือก")
    return Agg(sum(vals[q] for q in used) / len(used), used)


def span_text(qs_selected: list[int], used: list[int], f) -> str:
    """'ช่วงเวลา · ใช้ข้อมูล N ไตรมาส' (or 'ใช้ได้ X จาก Y ไตรมาสที่เลือก' when some selected quarters had no usable value)."""
    if not qs_selected:
        return ""
    y0, y1 = qs_selected[0] // 4, qs_selected[-1] // 4
    yr = f"พ.ศ. {y0}" if y0 == y1 else f"พ.ศ. {y0}–{y1}"
    only = "" if set(f.quarters) == {1, 2, 3, 4} else " · เฉพาะไตรมาส " + ", ".join(map(str, sorted(f.quarters)))
    n = f"ใช้ข้อมูล {len(used)} ไตรมาส" if len(used) == len(qs_selected) else f"ใช้ได้ {len(used)} จาก {len(qs_selected)} ไตรมาสที่เลือก"
    return f"{yr}{only} · {n}"
