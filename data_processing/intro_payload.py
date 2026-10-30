"""The small data package behind the intro animation (the film shown before the dashboard, and its MP4).

Everything in it is read from the validated tables of the dashboard: the latest value of four indicators (each with its own
quarter, never estimated) and the five-region map of Thailand drawn from the province boundaries. It is written to
``data/processed/intro_payload.json`` after every successful load, so the intro can start immediately on the next visit
while the dashboard is still loading."""
from __future__ import annotations

import json
import logging
import math

import pandas as pd

import config

log = logging.getLogger(__name__)

PAYLOAD = config.DATA_PROCESSED / "intro_payload.json"
REGION_COLORS = {"กรุงเทพมหานคร": "#ff6fb5", "ภาคเหนือ": "#ab46d2", "ภาคตะวันออกเฉียงเหนือ": "#55d8c1", "ภาคกลาง": "#fcf69c", "ภาคใต้": "#92d9f7"}
REGION_IDS = {"กรุงเทพมหานคร": "bkk", "ภาคเหนือ": "north", "ภาคตะวันออกเฉียงเหนือ": "ne", "ภาคกลาง": "central", "ภาคใต้": "south"}
_COS = 0.972      # cos(13.5 deg): the map is not stretched sideways
_Q = 3            # coordinates are rounded to 0.03 degree: plenty for a map shown ~800 px tall, and the file stays small


def _label(idx: int) -> str:
    return f"ไตรมาส {idx % 4 + 1}/{idx // 4}"


def _latest(df: pd.DataFrame | None, col: str):
    if df is None or len(df) == 0 or col not in df.columns:
        return None
    d = df.dropna(subset=[col])
    return None if d.empty else d.sort_values("period_idx").iloc[-1]


def _ring(ring) -> str:
    pts, last = [], None
    for lon, lat in ring:
        p = (round(lon * _COS * 100 / _Q) * _Q, round(-lat * 100 / _Q) * _Q)
        if p != last:
            pts.append(p)
            last = p
    return ("M" + "L".join(f"{x} {y}" for x, y in pts) + "Z") if len(pts) >= 3 else ""


def _map(b) -> dict | None:
    if b.geo is None or not b.has("province_region"):
        return None
    pr = b.get("province_region")
    year = int(pr["year_be"].max())
    reg_of = dict(zip(pr[pr["year_be"] == year]["iso"], pr[pr["year_be"] == year]["region"]))
    parts: dict[str, list[str]] = {}
    xs, ys = [], []
    for ft in b.geo["features"]:
        region = reg_of.get(ft.get("id"))
        if region not in REGION_COLORS:
            continue
        g = ft["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            for ring in poly:
                d = _ring(ring)
                if d:
                    parts.setdefault(region, []).append(d)
                    for lon, lat in ring:
                        xs.append(lon * _COS * 100)
                        ys.append(-lat * 100)
    if not parts:
        return None
    pad = 12
    box = [math.floor(min(xs)) - pad, math.floor(min(ys)) - pad, math.ceil(max(xs) - min(xs)) + 2 * pad, math.ceil(max(ys) - min(ys)) + 2 * pad]
    return {"viewBox": box, "year": year,
            "regions": [{"id": REGION_IDS[r], "name": r, "color": REGION_COLORS[r], "d": "".join(ds)} for r, ds in parts.items()]}


def build(b) -> dict:
    """The payload (KPI values with their own quarter + the map). Missing pieces are simply absent: the intro then leaves them out."""
    kpis = []
    nat, lm, emp = b.get("national"), b.get("lm_national"), b.get("lm_employed_national")
    r = _latest(lm, "emp_pct")
    if r is not None:
        kpis.append({"key": "emp", "label": "อัตราการมีงานทำ", "value": float(r["emp_pct"]), "dec": 2, "unit": "%", "period": _label(int(r["period_idx"]))})
    r = _latest(nat, "rate_pct")
    if r is not None:
        kpis.append({"key": "unemp", "label": "อัตราการว่างงาน", "value": float(r["rate_pct"]), "dec": 2, "unit": "%", "period": _label(int(r["period_idx"]))})
    r = _latest(lm, "wage")
    if r is not None:
        kpis.append({"key": "wage", "label": "ค่าจ้างเฉลี่ยต่อเดือน", "value": float(r["wage"]), "dec": 0, "unit": "บาท", "period": _label(int(r["period_idx"]))})
    r = _latest(emp, "emp_k")
    if r is not None:
        kpis.append({"key": "emp_n", "label": "จำนวนผู้มีงานทำ", "value": float(r["emp_k"]) / 1000.0, "dec": 2, "unit": "ล้านคน", "period": _label(int(r["period_idx"]))})
    return {"kpis": kpis, "map": _map(b)}


def write(b) -> None:
    """Called after a successful load; a failure here must never break the dashboard."""
    try:
        data = build(b)
        PAYLOAD.parent.mkdir(parents=True, exist_ok=True)
        PAYLOAD.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    except Exception:   # noqa: BLE001
        log.exception("cannot write the intro payload")


def read() -> dict | None:
    try:
        return json.loads(PAYLOAD.read_text(encoding="utf-8")) if PAYLOAD.exists() else None
    except (OSError, json.JSONDecodeError):
        return None
