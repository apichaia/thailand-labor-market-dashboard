"""Home page in the 'dashboard' layout: four gradient cards, map + trend, regional wages + sex gap, provinces + scatter + insights.

Every number comes from the validated tables. A figure that has no trustworthy value for the quarter shows "ไม่มีข้อมูล",
and a card whose newest value is older than the selected quarter says which quarter it describes.
"""
from __future__ import annotations

import functools

import numpy as np
import pandas as pd
import streamlit as st

import config
from analytics import metrics
from analytics import selectors as sel_
from dashboard import charts, labour_page
from dashboard import components as ui
from dashboard import pages
from dashboard.pages import Ctx, _card_title, _ckey, _plabel, _plot, _src_url

NO_FILTER = sel_.Filters(year_min=0, year_max=9999)


# ---------------------------------------------------------------------------
# gradient cards
# ---------------------------------------------------------------------------


def _icon(paths: str) -> str:
    """A white line icon (24x24, drawn here from simple shapes) for the gradient cards."""
    return f'<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths}</svg>'


ICON_EMP = _icon('<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5"/><circle cx="17.5" cy="9" r="2.4"/><path d="M16.5 14.6c2.6.2 4.5 2 4.5 5"/>')
ICON_JOB = _icon('<rect x="3" y="7" width="18" height="13" rx="2.5"/><path d="M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7"/><path d="M3 12.5h18"/>')
ICON_WAGE = _icon('<rect x="2.5" y="6" width="19" height="12" rx="2.5"/><circle cx="12" cy="12" r="2.6"/><path d="M6 9.5v.01M18 14.5v.01"/>')
ICON_CROWD = _icon('<circle cx="12" cy="7.5" r="3"/><circle cx="5.5" cy="10" r="2.2"/><circle cx="18.5" cy="10" r="2.2"/><path d="M6.5 20c0-3.3 2.4-5.5 5.5-5.5s5.5 2.2 5.5 5.5"/><path d="M1.5 18c0-2.2 1.6-3.8 3.8-3.8M22.5 18c0-2.2-1.6-3.8-3.8-3.8"/>')



def _star(cx: float, cy: float, r: float) -> str:
    """Points of a five-pointed star centred on (cx, cy)."""
    import math

    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rad = r if k % 2 == 0 else r * 0.46
        pts.append(f"{cx + rad * math.cos(ang):.1f},{cy + rad * math.sin(ang):.1f}")
    return " ".join(pts)


def _spark(values: list, w: int = 160, h: int = 40) -> str:
    """The last quarters as little stars placed at their values (a faint dotted thread joins neighbours) and a bat flying on the
    newest one. Same positions the old white line had; a missing quarter has no star and the thread is never bridged."""
    pts = [(i, float(v)) for i, v in enumerate(values) if v is not None and v == v]
    if len(pts) < 2:
        return ""
    lo, hi = min(v for _, v in pts), max(v for _, v in pts)
    span = (hi - lo) or 1.0
    n = max(len(values) - 1, 1)

    def xy(i, v):
        return 10 + i / n * (w - 52), h - 8 - (v - lo) / span * (h - 24)      # room on the right for the bat, and a band that keeps it inside the card

    runs, cur = [], []
    for i, v in enumerate(values):
        if v is None or v != v:
            if cur:
                runs.append(cur)
            cur = []
        else:
            cur.append(xy(i, float(v)))
    if cur:
        runs.append(cur)
    d = " ".join("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in run) for run in runs if len(run) > 1)
    thread = f'<path d="{d}" pathLength="1" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="1.2" stroke-dasharray=".02 .02" />' if d else ""
    stars = "".join(f'<polygon class="st" style="animation-delay:{(k % 6) * 0.35:.2f}s" points="{_star(*xy(i, v), 5.2)}" fill="#fff"/>'
                    for k, (i, v) in enumerate(pts[:-1]))
    lx, ly = xy(*pts[-1])
    # a little bat flying along the newest value: wings flap (CSS), the body bobs
    wing = "M-1.4,-.4 C-4.6,-5.2 -9.6,-4.6 -12.4,-1 Q-10.6,-1.6 -9,.5 Q-7.4,-.6 -5.8,1.7 Q-4.2,.4 -1.4,2.6 Z"
    flower = (f'<g transform="translate({lx + 21:.1f},{ly - 8:.1f}) scale(1.4)"><g class="bat"><path class="wl" d="{wing}" fill="#fff"/><g transform="scale(-1,1)"><path class="wr" d="{wing}" fill="#fff"/></g>'
              '<ellipse cx="0" cy="1" rx="2.3" ry="3.3" fill="#fff"/><circle cx="0" cy="-2.6" r="2.2" fill="#fff"/>'
              '<path d="M-2,-3.8 L-1.6,-6.4 L-.3,-4.4 Z M2,-3.8 L1.6,-6.4 L.3,-4.4 Z" fill="#fff"/>'
              '<circle cx="-.9" cy="-2.8" r=".55" fill="#43334C"/><circle cx=".9" cy="-2.8" r=".55" fill="#43334C"/></g></g>')
    return f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="xMinYMid meet" aria-hidden="true">{thread}{stars}{flower}</svg>'


def _card(cls: str, icon: str, label: str, value, unit: str, delta: str, spark: str, scope: str = "", why: str = "", title: str = "") -> str:
    """Four lines on every card (label / value / change / period + scope) so all cards have the same height."""
    if value is None:
        body = f'<div class="gc-na">ไม่มีข้อมูล</div><div class="gc-delta">{ui.esc(why)}</div>'
    else:
        raw = str(value).replace(",", "")
        dec = len(raw.split(".")[1]) if "." in raw else 0
        num = f'<b class="num" data-count="{ui.esc(raw)}" data-dec="{dec}" data-sep="{1 if "," in str(value) else 0}">{ui.esc(value)}</b>'
        body = f'<div class="gc-value">{num}<span>{ui.esc(unit)}</span></div><div class="gc-delta">{delta}</div>'
    return (f'<div class="gcard {cls}" title="{ui.esc(title)}"><div class="gc-icon">{icon}</div>'
            f'<div class="gc-body"><div class="gc-label">{ui.esc(label)}</div>{body}<div class="gc-scope">{ui.esc(scope)}</div></div>'
            f'<div class="gc-spark">{spark}</div></div>')


def _series_upto(df: pd.DataFrame, col: str, idx: int, n: int = 12):
    """(latest valid row at or before idx, its value list for the sparkline)."""
    if df is None or len(df) == 0 or col not in df.columns:
        return None, []
    d = df[df["period_idx"] <= idx].sort_values("period_idx")
    valid = d.dropna(subset=[col])
    if valid.empty:
        return None, []
    last = valid.iloc[-1]
    win = d[d["period_idx"] > int(last["period_idx"]) - n].set_index("period_idx")[col]
    full = [win.get(i, np.nan) for i in range(int(last["period_idx"]) - n + 1, int(last["period_idx"]) + 1)]
    return last, full


def _yoy_changes(df: pd.DataFrame, col: str, kind: str) -> pd.Series:
    """Change versus the same quarter one year earlier for every quarter ('pt' = points, 'pct' = percent); never bridges a gap."""
    s = df.drop_duplicates("period_idx").set_index("period_idx")[col].sort_index()
    if s.empty:
        return s
    full = s.reindex(range(int(s.index.min()), int(s.index.max()) + 1))
    prev = full.shift(4)
    return (full - prev) if kind == "pt" else (full / prev.where(prev != 0) - 1) * 100


def _delta_text(df: pd.DataFrame, col: str, row, kind: str, dec: int) -> str:
    """Change versus the same quarter last year ('pt' = percentage points, 'pct' = percent), with a flag when it is unusually large."""
    idx = int(row["period_idx"])
    d = _yoy_changes(df, col, kind).get(idx, np.nan)
    if pd.isna(d):
        return "ไม่มีข้อมูลปีก่อน"
    arrow = "▲" if d > 0 else ("▼" if d < 0 else "■")
    unit = " จุด" if kind == "pt" else "%"
    return f"{arrow} {d:+.{dec}f}{unit} <small>จากปีก่อน</small>"


_scoped_series = sel_.lm_scoped_series


def _kpi_row(ctx: Ctx, idx: int, sel) -> None:
    b, f = ctx.bundle, ctx.filters
    emp, wage, hcm, scope, notes = _scoped_series(b, f)
    c1, c2, c3, c4 = st.container(key="kpi_row").columns([1.2, 1, 1, 1], gap="small")   # 2 x 2 on phones (theme.CSS_BENTO)

    def line(row) -> str:
        p = int(row["period_idx"])
        return f"{_plabel(p)} · "

    # 1 employment rate
    r, vals = _series_upto(emp, "emp_pct", idx)
    c1.markdown(_card("g1", ICON_EMP, "อัตราการมีงานทำ", None if r is None else f"{r['emp_pct']:.2f}", "%" if r is not None else "",
                      "" if r is None else _delta_text(emp, "emp_pct", r, "pt", 2), _spark(vals),
                      "" if r is None else line(r) + scope, "ไม่มีค่าที่เชื่อถือได้ในกลุ่มนี้", "สสช. OS_02_0016_03 · " + scope), unsafe_allow_html=True)
    # 2 unemployment rate: always follows every sidebar filter
    d = sel.data
    r, vals = _series_upto(d, "rate_pct", idx)
    u_scope = "ทั่วประเทศ" if not (f.regions or f.sexes or f.edu_active) else "ตามตัวกรอง"
    c2.markdown(_card("g2", ICON_JOB, "อัตราการว่างงาน", None if r is None else f"{r['rate_pct']:.2f}", "%" if r is not None else "",
                      "" if r is None else _delta_text(d, "rate_pct", r, "pt", 2), _spark(vals),
                      "" if r is None else line(r) + u_scope, "ไม่มีตัวหารกำลังแรงงานภายใต้ตัวกรองนี้", "สสช. · ผู้ว่างงาน ÷ กำลังแรงงาน"), unsafe_allow_html=True)
    # 3 wage
    r, vals = _series_upto(wage, "wage", idx)
    c3.markdown(_card("g3", ICON_WAGE, "ค่าจ้างเฉลี่ยต่อเดือน", None if r is None else f"{r['wage']:,.0f}", "บาท" if r is not None else "",
                      "" if r is None else _delta_text(wage, "wage", r, "pct", 1), _spark(vals),
                      "" if r is None else line(r) + scope, "ไม่มีค่าที่เชื่อถือได้ในกลุ่มนี้", "สสช. OS_02_0024_01 · ราคาปัจจุบัน · " + scope), unsafe_allow_html=True)
    # 4 employed persons (file received from a friend, checked against NSO)
    r, vals = _series_upto(hcm, "emp_m", idx)
    c4.markdown(_card("g4", ICON_CROWD, "จำนวนผู้มีงานทำ", None if r is None else f"{r['emp_m']:.2f}", "ล้านคน" if r is not None else "",
                      "" if r is None else _delta_text(hcm, "emp_m", r, "pct", 1), _spark(vals),
                      "" if r is None else line(r) + hcm.attrs.get("scope", scope), "ไม่มีข้อมูลในกลุ่มนี้", "สสช. OS_02_0002_01 ตรวจกับ LFS_02_20535_1 · " + hcm.attrs.get("scope", scope)), unsafe_allow_html=True)
    for n in notes:
        st.caption(":material/info: " + n)


# ---------------------------------------------------------------------------
# cards that hold charts
# ---------------------------------------------------------------------------

MAP_METRICS = {"อัตรามีงานทำ (%)": ("emp_pct", "อัตรามีงานทำ", "%", 2), "อัตราการว่างงาน (%)": ("rate_pct", "อัตราการว่างงาน", "%", 2),
               "ค่าจ้างเฉลี่ย (บาท)": ("wage", "ค่าจ้างเฉลี่ย", "บาท", 0)}


def _latest_region_period(rs: pd.DataFrame, col: str, upto: int, need: int = 5) -> int | None:
    if col not in rs.columns:
        return None
    d = rs[(rs["period_idx"] <= upto)].dropna(subset=[col])
    cnt = d.groupby("period_idx").size()
    ok = cnt[cnt >= need]
    return int(ok.index.max()) if len(ok) else None


def _sexage_period(sa: pd.DataFrame, idx: int) -> int | None:
    """Newest quarter at or before idx with wages for (nearly) every sex x age group."""
    if not len(sa):
        return None
    d = sa[sa["sex"].isin(["ชาย", "หญิง"]) & (sa["age_group"] != "รวม") & (sa["period_idx"] <= idx)].dropna(subset=["wage"])
    cnt = d.groupby("period_idx").size()
    ok = cnt[cnt >= 14]
    return int(ok.index.max()) if len(ok) else None


def _period_strip(ctx: Ctx, idx: int) -> None:
    """One line of chips saying which quarter each part of the page shows; a part older than the cards is marked."""
    b = ctx.bundle
    rs = b.get("region_series")
    map_col = MAP_METRICS[st.session_state.get("ov_map_metric", next(iter(MAP_METRICS)))][0]
    parts = [("การ์ดตัวชี้วัด", idx), ("แผนที่", _latest_region_period(rs, map_col, idx)),
             ("ค่าจ้างรายภาค", _latest_region_period(rs, "wage", idx)), ("ค่าจ้างชาย-หญิง", _sexage_period(b.get("lm_sex_age"), idx)),
             ("อันดับภูมิภาค", _latest_region_period(rs, "rate_pct", idx))]
    chips = []
    for name, p in parts:
        if p is None:
            chips.append(f'<span class="pchip na">{ui.esc(name)} · ไม่มีข้อมูล</span>')
        else:
            old = p < idx
            chips.append(f'<span class="pchip{" old" if old else ""}" title="{"เก่ากว่าการ์ด เพราะยังไม่มีค่าที่ผ่านการตรวจสอบในไตรมาสที่ใหม่กว่า" if old else ""}">'
                         f'{ui.esc(name)} · <b>{ui.esc(_plabel(p))}</b></span>')
    st.markdown('<div class="pstrip"><span class="pstrip-t">ข้อมูลในหน้านี้</span>' + "".join(chips)
                + '<span class="pstrip-k"><i></i>เก่ากว่าการ์ด</span></div>', unsafe_allow_html=True)


_MAP = pages.REGION_MAP
_show_whole_country = pages.show_whole_country


def _map_and_trend(ctx: Ctx, idx: int, sel) -> None:
    b, f = ctx.bundle, ctx.filters
    rs = b.get("region_series")
    m1, m2 = st.columns([1, 1.55], gap="small")
    with m1:
        with st.container(border=True, key=_ckey()):
            h1, h2 = st.columns([1.3, 1], vertical_alignment="center")
            with h1:
                _card_title("แผนที่ตลาดแรงงานรายภูมิภาค")
            with h2:
                choice = st.selectbox("ตัวชี้วัดบนแผนที่", list(MAP_METRICS), key="ov_map_metric", label_visibility="collapsed")
            col, label, unit, dec = MAP_METRICS[choice]
            p = _latest_region_period(rs, col, idx)
            if p is None:
                ui.empty_state("ไม่มีข้อมูลรายภาคที่ผ่านการตรวจสอบสำหรับตัวชี้วัดนี้")
            else:
                mp = sel_.region_map_frame(b, NO_FILTER, p, col)
                if mp.empty:
                    ui.empty_state(mp.unavailable_reason or "ไม่มีข้อมูลสำหรับแผนที่")
                else:
                    zoom = [r for r in f.regions if r in set(mp.data["region"])]
                    data = mp.data[mp.data["region"].isin(zoom)] if zoom else mp.data
                    svg = charts.region_svg_map(b.geo, data, label, unit, dec)
                    if svg is None:
                        ui.empty_state("ภาคนี้ไม่มีค่าของตัวชี้วัดนี้ในไตรมาสที่เลือก ไม่ประมาณค่าแทน" if zoom else "ไตรมาสนี้ไม่มีค่าให้แสดงบนแผนที่ ไม่ประมาณค่าแทน")
                        if zoom:
                            st.button("← ดูทั้งประเทศ", key="ov_map_back_empty", on_click=_show_whole_country)
                    else:
                        key = "ov_map_fig_" + ("|".join(zoom) if zoom else "all")
                        _MAP(data=svg, key=key, on_region_change=functools.partial(pages.on_map_click, key))
                        st.markdown(charts.region_map_legend(data, label, unit, dec, vertical=True), unsafe_allow_html=True)
                        if zoom:
                            st.button("← ดูทั้งประเทศ", key="ov_map_back", on_click=_show_whole_country)
                        st.caption(f"{_plabel(p)}" + ("" if p == idx else " (ไตรมาสล่าสุดที่มีค่าของตัวชี้วัดนี้)")
                                   + (" · ทั้งหน้านี้แสดงเฉพาะภาคที่เลือก" if zoom else " · คลิกที่ภูมิภาคเพื่อขยายและดูเฉพาะภาคนั้น"))
    with m2:
        with st.container(border=True, key=_ckey()):
            h1, h2 = st.columns([1.3, 1], vertical_alignment="center")
            with h1:
                _card_title("แนวโน้มรายไตรมาส")
            with h2:
                tchoice = st.selectbox("ตัวชี้วัดแนวโน้ม", ["อัตรามีงานทำ", "อัตราการว่างงาน", "ค่าจ้างเฉลี่ย", "จำนวนผู้ว่างงาน"], key="ov_trend_choice",
                                       label_visibility="collapsed")
            emp_s, wage_s, _hc, t_scope, _n = _scoped_series(b, f)
            tf = f.for_trend()   # the whole 2563+ scope; the picked years are shaded
            lmn_e, lmn_w = sel_.in_time(emp_s, tf), sel_.in_time(wage_s, tf)
            full = metrics.add_changes(sel.data, "u_k")
            win = sel_.in_time(full, tf)
            if tchoice == "อัตรามีงานทำ":
                df, col, ttl, u, dec = lmn_e, "emp_pct", "อัตรามีงานทำ", "ร้อยละ", 2
            elif tchoice == "ค่าจ้างเฉลี่ย":
                df, col, ttl, u, dec = lmn_w, "wage", "ค่าจ้างเฉลี่ย", "บาท/เดือน", 0
            elif tchoice == "อัตราการว่างงาน":
                df, col, ttl, u, dec = win, "rate_pct", "อัตราการว่างงาน", "ร้อยละ", 2
            else:
                df, col, ttl, u, dec = pages.persons(win), "u_k", "จำนวนผู้ว่างงาน", "คน", 0
            if df is None or len(df) == 0 or df[col].notna().sum() < 2:
                ui.empty_state("ไม่มีข้อมูลที่ผ่านการตรวจสอบเพียงพอในช่วงที่เลือก")
            else:
                st.plotly_chart(charts.trend_line(df, col, ttl, u, height=340, decimals=dec, focus=f.focus), width="stretch", key=f"ov_trend_{col}",
                                config={"displayModeBar": False})
                miss = df[df[col].isna()]["period_label"].tolist()
                if miss:
                    st.caption("ช่องว่าง = ไม่มีค่าที่เชื่อถือได้ (" + ", ".join(miss[:4]) + (" …" if len(miss) > 4 else "") + ") ไม่เติมค่า")
                if col in ("emp_pct", "wage"):
                    st.caption(f"ขอบเขต: {t_scope}" + ("" if t_scope != "ทั่วประเทศ" else " · ไม่ใช้ตัวกรองการศึกษาหรือภาคร่วมกับเพศ"))
        _wage_cards(ctx, idx)   # the two smaller cards sit under the trend, next to the tall map (bento block)


def _wage_cards(ctx: Ctx, idx: int) -> None:
    b = ctx.bundle
    rs = b.get("region_series")
    sa = b.get("lm_sex_age")
    c1, c2 = st.columns([1, 1.15], gap="small")
    with c1:
        with st.container(border=True, key=_ckey()):
            p = _latest_region_period(rs, "wage", idx)
            _card_title("ภูมิภาคที่มีค่าจ้างสูงสุด", f"จัดอันดับ 5 ภาค · บาทต่อเดือน · {_plabel(p)}" if p else "")
            if p is None:
                ui.empty_state("ไม่มีค่าจ้างรายภาคที่ผ่านการตรวจสอบ")
            else:
                d = rs[rs["period_idx"] == p].dropna(subset=["wage"])
                st.markdown(region_rank_html(d, "wage", "", 0, list(ctx.filters.regions)), unsafe_allow_html=True)
                if ctx.filters.regions:
                    st.caption("แท่งเข้ม = ภาคที่เลือกในตัวกรอง · ภาคอื่นจางลงเพื่อให้เทียบกันได้")
    with c2:
        with st.container(border=True, key=_ckey()):
            p = _sexage_period(sa, idx)
            if p is None:
                _card_title("ค่าจ้างชาย-หญิงตามกลุ่มอายุ")
                ui.empty_state("ไม่มีค่าจ้างเพศ×อายุที่ผ่านการตรวจสอบ")
            else:
                cur = sa[sa["sex"].isin(["ชาย", "หญิง"]) & (sa["age_group"] != "รวม") & (sa["period_idx"] == p)].dropna(subset=["wage"])
                ages = [a for a in ["15-19 ปี", "20-24 ปี", "25-29 ปี", "30-34 ปี", "35-39 ปี", "40-49 ปี", "50-59 ปี", "60 ปีขึ้นไป"] if a in set(cur["age_group"])]
                cur = cur.assign(age_group=pd.Categorical(cur["age_group"], ages, ordered=True)).sort_values("age_group")
                _card_title("ค่าจ้างชาย-หญิงตามกลุ่มอายุ", f"บาทต่อเดือน · {_plabel(p)}")
                _plot_inline(charts.grouped_bar(cur, "age_group", "wage", "sex", "ค่าจ้างเฉลี่ย", "บาท/เดือน", 0), "ov_sexage", 340)


def _plot_inline(fig, key: str, height: int | None = None) -> None:
    if height:
        fig.update_layout(height=height)
    st.plotly_chart(fig, width="stretch", key=key, config={"displayModeBar": False})


def corr_phrase(r: float) -> str:
    """Thai wording for a Pearson r that does not claim more than its size: |r| < .1 none, < .3 weak, < .5 moderate, else strong."""
    a = abs(r)
    if a < 0.1:
        return "แทบไม่สัมพันธ์กัน"
    strength = "ระดับอ่อน" if a < 0.3 else ("ระดับปานกลาง" if a < 0.5 else "ระดับสูง")
    return f"สัมพันธ์{'เชิงลบ' if r < 0 else 'เชิงบวก'}{strength}"


def _insights(ctx: Ctx, idx: int, r: float | None) -> list[tuple[str, str]]:
    """Up to four sentences made only of numbers that are on this page."""
    b = ctx.bundle
    rs = b.get("region_series")
    out = []
    pe = _latest_region_period(rs, "emp_pct", idx)
    if pe is not None:
        d = rs[rs["period_idx"] == pe].dropna(subset=["emp_pct"])
        top = d.loc[d["emp_pct"].idxmax()]
        low = d.loc[d["emp_pct"].idxmin()]
        out.append((f"{top['region']}มีอัตรามีงานทำสูงสุด {top['emp_pct']:.1f}%", f"{_plabel(pe)} · ต่ำสุดคือ{low['region']} {low['emp_pct']:.1f}%"))
    pw = _latest_region_period(rs, "wage", idx)
    if pw is not None:
        d = rs[rs["period_idx"] == pw].dropna(subset=["wage"])
        top = d.loc[d["wage"].idxmax()]
        low = d.loc[d["wage"].idxmin()]
        out.append((f"{top['region']}มีค่าจ้างเฉลี่ยสูงสุด ฿{top['wage']:,.0f}",
                    f"{_plabel(pw)} · สูงกว่า{low['region']} (฿{low['wage']:,.0f}) {(top['wage'] / low['wage'] - 1) * 100:.0f}%"))
    pu = _latest_region_period(rs, "rate_pct", idx)
    if pu is not None:
        d = rs[rs["period_idx"] == pu].dropna(subset=["rate_pct"])
        top = d.loc[d["rate_pct"].idxmax()]
        low = d.loc[d["rate_pct"].idxmin()]
        out.append((f"{top['region']}มีอัตราการว่างงานสูงสุด {top['rate_pct']:.2f}%", f"{_plabel(pu)} · ต่ำสุดคือ{low['region']} {low['rate_pct']:.2f}%"))
    if r is not None:
        out.append((f"ค่าจ้างกับอัตราการว่างงาน{corr_phrase(r)} (r = {r:.2f})", "เป็นความสัมพันธ์เชิงสถิติ ไม่ใช่เหตุและผล"))
    return out


def region_rank_html(d: pd.DataFrame, col: str, unit: str, dec: int, highlight=()) -> str:
    """A ranked list: number, name, value and a bar scaled to the largest value (highest first)."""
    d = d.dropna(subset=[col]).sort_values(col, ascending=False)
    if d.empty:
        return ""
    top = float(d[col].max()) or 1.0
    rows = []
    for n, r in enumerate(d.itertuples(index=False), 1):
        v = float(getattr(r, col))
        dim = " dim" if highlight and r.region not in highlight else ""
        rows.append(f'<div class="rk{dim}"><span class="rk-n">{n}</span><div class="rk-b"><div class="rk-t"><b>{ui.esc(r.region)}</b><span>{v:,.{dec}f}{unit}</span></div>'
                    f'<div class="rk-bar"><i style="width:{max(v / top * 100, 2):.1f}%"></i></div></div></div>')
    return '<div class="rklist">' + "".join(rows) + "</div>"


def _province_scatter_insights(ctx: Ctx, idx: int) -> None:
    b = ctx.bundle
    p1, p2, p3 = st.columns([1.05, 1.15, 1], gap="small")
    with p1:
        with st.container(border=True, key=_ckey()):
            rs = b.get("region_series")
            p = _latest_region_period(rs, "rate_pct", idx)
            if p is None:
                _card_title("ภูมิภาคที่อัตราการว่างงานสูงสุด")
                ui.empty_state("ไม่มีอัตราการว่างงานรายภาคที่ผ่านการตรวจสอบ")
            else:
                _card_title("ภูมิภาคที่อัตราการว่างงานสูงสุด", f"จัดอันดับ 5 ภาค · {_plabel(p)}")
                d = rs[rs["period_idx"] == p].dropna(subset=["rate_pct"])
                st.markdown(region_rank_html(d, "rate_pct", "%", 2, list(ctx.filters.regions)), unsafe_allow_html=True)
                st.caption("แท่งเข้ม = ภาคที่เลือกในตัวกรอง" if ctx.filters.regions else "อัตราการว่างงาน = ผู้ว่างงาน ÷ กำลังแรงงาน · ภาคที่ไม่มีค่าที่ตรวจสอบแล้วไม่ถูกจัดอันดับ")
    r_val = None
    with p2:
        with st.container(border=True, key=_ckey()):
            _card_title("ความสัมพันธ์ระหว่างค่าจ้างกับการว่างงาน", "แต่ละจุดคือหนึ่งไตรมาส")
            fr, _sc, _nn = labour_page._scoped_frame(b, ctx.filters, config.JOINT_START_BE * 4, max(idx, config.JOINT_START_BE * 4 + 1))
            d = fr.dropna(subset=["rate_pct", "wage"])
            cs = metrics.correlation_summary(d["rate_pct"], d["wage"]) if len(d) >= 8 else {"reason": "ข้อมูลไม่เพียงพอ"}
            if cs.get("reason"):
                ui.empty_state(cs["reason"])
            else:
                r_val = cs["pearson"]
                _plot_inline(labour_page._scatter_figure(d, "wage", "ค่าจ้างเฉลี่ย", "บาท/เดือน"), "ov_scatter", 390)
                st.caption(f"r = {cs['pearson']:.2f} · n = {cs['n']} ไตรมาส · ไม่ใช่ความเป็นเหตุเป็นผล")
    with p3:
        with st.container(border=True, key=_ckey()):
            _card_title("สรุปจากข้อมูล", "สร้างจากตัวเลขในหน้านี้โดยอัตโนมัติ")
            items = _insights(ctx, idx, r_val)
            if not items:
                st.write("ยังไม่มีข้อมูลเพียงพอสำหรับสรุป")
            for n, (head, sub) in enumerate(items, 1):
                st.markdown(f'<div class="ins"><div class="n">{n}</div><div><b>{ui.esc(head)}</b><div class="s">{ui.esc(sub)}</div></div></div>',
                            unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# the page
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# side-by-side comparison: two regions, or two quarters
# ---------------------------------------------------------------------------

CMP_METRICS = {"อัตรามีงานทำ (%)": ("emp_pct", "อัตรามีงานทำ", "%", 2), "อัตราการว่างงาน (%)": ("rate_pct", "อัตราการว่างงาน", "%", 2),
               "ค่าจ้างเฉลี่ย (บาท)": ("wage", "ค่าจ้างเฉลี่ย", "บาท", 0)}
LINE_COLORS = dict(charts.REGION_COLORS, **{"ภาคกลาง": "#D4B800"})     # the pale yellow of the map is too faint for a line on white


def region_gap(rs: pd.DataFrame, a: str, b: str, col: str, idx: int) -> dict | None:
    """Latest valid value of each region at or before idx and the gap a - b (percent for wages, points for rates); None when either has no value."""
    vals = {}
    for r in (a, b):
        row, _ = _series_upto(rs[rs["region"] == r], col, idx)
        if row is None:
            return None
        vals[r] = (float(row[col]), int(row["period_idx"]))
    va, vb = vals[a][0], vals[b][0]
    gap = (va / vb * 100 - 100) if col == "wage" and vb else va - vb
    return {"a": vals[a], "b": vals[b], "gap": gap, "unit": "%" if col == "wage" else " จุด"}


def period_rows(emp, un, wage, p1: int, p2: int) -> list[dict]:
    """The three national indicators in two chosen quarters, with the change from the first to the second (blank when either quarter has no value)."""
    rows = []
    for name, df, col, dec, kind in (("อัตรามีงานทำ (%)", emp, "emp_pct", 2, "pt"), ("อัตราการว่างงาน (%)", un, "rate_pct", 2, "pt"), ("ค่าจ้างเฉลี่ย (บาท)", wage, "wage", 0, "pct")):
        v = []
        for p in (p1, p2):
            s = df[df["period_idx"] == p][col].dropna() if df is not None and col in df.columns else pd.Series(dtype=float)
            v.append(float(s.iloc[0]) if len(s) else None)
        diff = None if None in v else ((v[1] / v[0] * 100 - 100) if kind == "pct" and v[0] else v[1] - v[0])
        rows.append({"name": name, "v1": v[0], "v2": v[1], "diff": diff, "dec": dec, "unit": "%" if kind == "pct" else " จุด"})
    return rows


def _diff_text(r: dict) -> str:
    d = r["diff"]
    if d is None:
        return "ไม่มีข้อมูล"
    arrow = "▲" if d > 0 else ("▼" if d < 0 else "■")
    return f"{arrow} {abs(d):,.{1 if r['unit'] == '%' else 2}f}{r['unit']}"


def _fmt(v, dec: int) -> str:
    return "ไม่มีข้อมูล" if v is None else f"{v:,.{dec}f}"


def _compare(ctx: Ctx, idx: int, sel) -> None:
    b, f = ctx.bundle, ctx.filters
    mode = st.radio("เปรียบเทียบ", ["สองภูมิภาค", "สองไตรมาส"], horizontal=True, key="cmp_mode", label_visibility="collapsed")
    if mode == "สองภูมิภาค":
        rs = b.get("region_series")
        regions = [r for r in charts.REGION_ORDER if rs is not None and r in set(rs["region"])]
        if len(regions) < 2:
            ui.empty_state("ไม่มีข้อมูลรายภาคเพียงพอสำหรับเปรียบเทียบ")
            return
        c1, c2, c3 = st.columns(3)
        ra = c1.selectbox("ภูมิภาค A", regions, index=regions.index("ภาคเหนือ") if "ภาคเหนือ" in regions else 0, key="cmp_a")
        rb = c2.selectbox("ภูมิภาค B", [r for r in regions if r != ra], index=0, key="cmp_b")
        mname = c3.selectbox("ตัวชี้วัด", list(CMP_METRICS), key="cmp_metric")
        col, label, unit, dec = CMP_METRICS[mname]
        g = region_gap(rs, ra, rb, col, idx)
        if g is None:
            ui.empty_state("อย่างน้อยหนึ่งภูมิภาคไม่มีค่าที่ตรวจสอบแล้วของตัวชี้วัดนี้ ไม่ประมาณค่าแทน")
        else:
            va, pa = g["a"]
            vb, pb = g["b"]
            head = "เท่ากัน" if round(g["gap"], 2) == 0 else f"{ra} {'สูงกว่า' if g['gap'] > 0 else 'ต่ำกว่า'}{rb} {abs(g['gap']):,.{1 if col == 'wage' else 2}f}{g['unit']}"
            st.markdown(f'<div class="story cmp"><div class="story-t">{ui.esc(label)}<small>ค่าล่าสุดที่ตรวจสอบแล้วของแต่ละภาค</small></div><div class="story-i">'
                        f'<div class="sf"><i style="background:{LINE_COLORS[ra]}"></i><div><span><b>{ui.esc(ra)}</b> {va:,.{dec}f} {unit}</span><small>{ui.esc(_plabel(pa))}</small></div></div>'
                        f'<div class="sf"><i style="background:{LINE_COLORS[rb]}"></i><div><span><b>{ui.esc(rb)}</b> {vb:,.{dec}f} {unit}</span><small>{ui.esc(_plabel(pb))}</small></div></div>'
                        f'<div class="sf"><i>◆</i><div><span>{ui.esc(head)}</span><small>{"ต่างกันเป็นร้อยละของ B" if col == "wage" else "ต่างกันเป็นจุดร้อยละ"}</small></div></div>'
                        f'</div></div>', unsafe_allow_html=True)
            d = rs[rs["region"].isin([ra, rb])]
            if d[col].notna().sum() >= 2:
                st.plotly_chart(charts.multi_line(d, col, "region", label, unit, decimals=dec, height=360, focus=f.focus, colors=LINE_COLORS),
                                width="stretch", key=f"cmp_line_{col}_{ra}_{rb}", config={"displayModeBar": False})
                st.caption("เส้นขาด = ไตรมาสที่ไม่มีค่าที่เชื่อถือได้ (ไม่เติมค่า)")
    else:
        periods = sorted({int(p) for p in sel.data["period_idx"]}, reverse=True)
        c1, c2 = st.columns(2)
        p1 = c1.selectbox("ไตรมาสแรก", periods, index=min(4, len(periods) - 1), format_func=_plabel, key="cmp_p1")
        p2 = c2.selectbox("ไตรมาสที่สอง", periods, index=0, format_func=_plabel, key="cmp_p2")
        emp, wage, _h, scope, _n = _scoped_series(b, f)
        rows = period_rows(emp, sel.data, wage, p1, p2)
        body = "".join(f"<tr><td>{ui.esc(r['name'])}</td><td>{_fmt(r['v1'], r['dec'])}</td><td>{_fmt(r['v2'], r['dec'])}</td><td>{_diff_text(r)}</td></tr>" for r in rows)
        st.markdown(f'<table class="cmp-t"><thead><tr><th></th><th>{ui.esc(_plabel(p1))}</th><th>{ui.esc(_plabel(p2))}</th><th>เปลี่ยนแปลง</th></tr></thead><tbody>{body}</tbody></table>',
                    unsafe_allow_html=True)
        st.caption(f"ขอบเขต: {scope} · ช่องที่ไม่มีค่าที่เชื่อถือได้แสดง \"ไม่มีข้อมูล\" ไม่ประมาณค่าแทน")


def home(ctx: Ctx) -> None:

    b, f = ctx.bundle, ctx.filters
    sel = sel_.unemployed_series(b, f)
    idx = sel_.kpi_period(sel, f) if not sel.empty else None
    if idx is None:
        ui.empty_state(sel.unavailable_reason if not sel.empty and sel.unavailable_reason else "ไม่มีข้อมูลในช่วงเวลาและตัวกรองที่เลือก กรุณาขยายช่วงปีหรือกดล้างตัวกรอง")
        return
    _kpi_row(ctx, idx, sel)
    _period_strip(ctx, idx)
    _map_and_trend(ctx, idx, sel)
    _province_scatter_insights(ctx, idx)
    # extra sections are built only when asked for: they are heavy, and a folded section used to be computed on every click anyway
    more = st.segmented_control("รายละเอียดเพิ่มเติม", ["เปรียบเทียบ", "แนวโน้ม 3 ตัวชี้วัดและความสัมพันธ์", "เทียบกับเศรษฐกิจ (GDP)"], key="ov_more",
                                help="เลือกเพื่อเปิดส่วนที่ละเอียดกว่า กดซ้ำเพื่อปิด (ส่วนนี้ไม่ถูกคำนวณจนกว่าจะเปิด เพื่อให้หน้าตอบสนองเร็ว)")
    if more == "เปรียบเทียบ":
        _compare(ctx, idx, sel)
    elif more == "แนวโน้ม 3 ตัวชี้วัดและความสัมพันธ์":
        labour_page.national_section(ctx)
    elif more == "เทียบกับเศรษฐกิจ (GDP)":
        pages.economic(ctx)
