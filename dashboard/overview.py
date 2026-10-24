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


def _spark(values: list, w: int = 128, h: int = 44) -> str:
    """Tiny line of the last quarters; a missing quarter breaks the line (never bridged)."""
    pts = [(i, float(v)) for i, v in enumerate(values) if v is not None and v == v]
    if len(pts) < 2:
        return ""
    lo, hi = min(v for _, v in pts), max(v for _, v in pts)
    span = (hi - lo) or 1.0
    n = max(len(values) - 1, 1)

    def xy(i, v):
        return 4 + i / n * (w - 8), h - 5 - (v - lo) / span * (h - 12)

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
    lx, ly = xy(*pts[-1])
    return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true"><path d="{d}" fill="none" stroke="#fff" '
            f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="{lx:.1f}" cy="{ly:.1f}" r="3.6" fill="#fff"/></svg>')


def _card(cls: str, icon: str, label: str, value, unit: str, delta: str, spark: str, scope: str = "", why: str = "", title: str = "") -> str:
    """Four lines on every card (label / value / change / period + scope) so all cards have the same height."""
    if value is None:
        body = f'<div class="gc-na">ไม่มีข้อมูล</div><div class="gc-delta">{ui.esc(why)}</div>'
    else:
        body = f'<div class="gc-value">{ui.esc(value)}<span>{ui.esc(unit)}</span></div><div class="gc-delta">{delta}</div>'
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


def _delta_text(df: pd.DataFrame, col: str, row, kind: str, dec: int) -> str:
    """Change versus the same quarter last year ('pt' = percentage points, 'pct' = percent)."""
    s = df.drop_duplicates("period_idx").set_index("period_idx")[col]
    prev = s.get(int(row["period_idx"]) - 4, np.nan)
    cur = row[col]
    if pd.isna(prev) or pd.isna(cur):
        return "ไม่มีข้อมูลปีก่อน"
    if kind == "pt":
        d = float(cur - prev)
        return f"{'▲' if d > 0 else ('▼' if d < 0 else '■')} {d:+.{dec}f} จุด <small>จากปีก่อน</small>"
    d = (float(cur) / float(prev) - 1) * 100 if prev else float("nan")
    return f"{'▲' if d > 0 else ('▼' if d < 0 else '■')} {d:+.{dec}f}% <small>จากปีก่อน</small>"


_scoped_series = sel_.lm_scoped_series


def _kpi_row(ctx: Ctx, idx: int, sel) -> None:
    b, f = ctx.bundle, ctx.filters
    emp, wage, hcm, scope, notes = _scoped_series(b, f)
    c1, c2, c3, c4 = st.columns(4, gap="small")

    def line(row) -> str:
        p = int(row["period_idx"])
        return f"{_plabel(p)} · "

    # 1 employment rate
    r, vals = _series_upto(emp, "emp_pct", idx)
    c1.markdown(_card("g1", "👥", "อัตราการมีงานทำ", None if r is None else f"{r['emp_pct']:.2f}", "%" if r is not None else "",
                      "" if r is None else _delta_text(emp, "emp_pct", r, "pt", 2), _spark(vals),
                      "" if r is None else line(r) + scope, "ไม่มีค่าที่เชื่อถือได้ในกลุ่มนี้", "สสช. OS_02_0016_03 · " + scope), unsafe_allow_html=True)
    # 2 unemployment rate: always follows every sidebar filter
    d = sel.data
    r, vals = _series_upto(d, "rate_pct", idx)
    u_scope = "ทั่วประเทศ" if not (f.regions or f.sexes or f.edu_active) else "ตามตัวกรอง"
    c2.markdown(_card("g2", "💼", "อัตราการว่างงาน", None if r is None else f"{r['rate_pct']:.2f}", "%" if r is not None else "",
                      "" if r is None else _delta_text(d, "rate_pct", r, "pt", 2), _spark(vals),
                      "" if r is None else line(r) + u_scope, "ไม่มีตัวหารกำลังแรงงานภายใต้ตัวกรองนี้", "สสช. · ผู้ว่างงาน ÷ กำลังแรงงาน"), unsafe_allow_html=True)
    # 3 wage
    r, vals = _series_upto(wage, "wage", idx)
    c3.markdown(_card("g3", "💰", "ค่าจ้างเฉลี่ยต่อเดือน", None if r is None else f"{r['wage']:,.0f}", "บาท" if r is not None else "",
                      "" if r is None else _delta_text(wage, "wage", r, "pct", 1), _spark(vals),
                      "" if r is None else line(r) + scope, "ไม่มีค่าที่เชื่อถือได้ในกลุ่มนี้", "สสช. OS_02_0024_01 · ราคาปัจจุบัน · " + scope), unsafe_allow_html=True)
    # 4 employed persons (file received from a friend, checked against NSO)
    r, vals = _series_upto(hcm, "emp_m", idx)
    c4.markdown(_card("g4", "🧑‍🤝‍🧑", "จำนวนผู้มีงานทำ", None if r is None else f"{r['emp_m']:.2f}", "ล้านคน" if r is not None else "",
                      "" if r is None else _delta_text(hcm, "emp_m", r, "pct", 1), _spark(vals),
                      "" if r is None else line(r) + hcm.attrs.get("scope", scope), "ไม่มีข้อมูลในกลุ่มนี้", "จากไฟล์ที่ได้รับ ตรวจกับ สสช. ได้เฉพาะ 2563+ · " + hcm.attrs.get("scope", scope)), unsafe_allow_html=True)
    for n in notes:
        st.caption("ℹ️ " + n)


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


_MAP = pages.REGION_MAP
_show_whole_country = pages.show_whole_country


def _map_and_trend(ctx: Ctx, idx: int, sel) -> None:
    b, f = ctx.bundle, ctx.filters
    rs = b.get("region_series")
    m1, m2 = st.columns([1.15, 1], gap="small")
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
                        left, right = st.columns([1.2, 1], gap="small", vertical_alignment="center")
                        with left:
                            _MAP(data=svg, key=key, on_region_change=functools.partial(pages.on_map_click, key))
                        with right:
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
            lmn_e, lmn_w = sel_.in_time(emp_s, f), sel_.in_time(wage_s, f)
            full = metrics.add_changes(sel.data, "u_k")
            win = sel_.in_time(full, f)
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
                st.plotly_chart(charts.trend_line(df, col, ttl, u, height=340, decimals=dec), width="stretch", key=f"ov_trend_{col}",
                                config={"displayModeBar": False})
                miss = df[df[col].isna()]["period_label"].tolist()
                if miss:
                    st.caption("ช่องว่าง = ไม่มีค่าที่เชื่อถือได้ (" + ", ".join(miss[:4]) + (" …" if len(miss) > 4 else "") + ") ไม่เติมค่า")
                if col in ("emp_pct", "wage"):
                    st.caption(f"ขอบเขต: {t_scope}" + ("" if t_scope != "ทั่วประเทศ" else " · ไม่ใช้ตัวกรองการศึกษาหรือภาคร่วมกับเพศ"))


def _wage_cards(ctx: Ctx, idx: int) -> None:
    b = ctx.bundle
    rs = b.get("region_series")
    sa = b.get("lm_sex_age")
    c1, c2 = st.columns([1, 1.15], gap="small")
    with c1:
        with st.container(border=True, key=_ckey()):
            p = _latest_region_period(rs, "wage", idx)
            _card_title("ภูมิภาคที่มีค่าจ้างสูงสุด", f"ค่าจ้างเฉลี่ยต่อเดือน (บาท) · {_plabel(p)}" if p else "")
            if p is None:
                ui.empty_state("ไม่มีค่าจ้างรายภาคที่ผ่านการตรวจสอบ")
            else:
                d = rs[rs["period_idx"] == p].dropna(subset=["wage"])
                _plot_inline(charts.region_bar(d, "wage", "ค่าจ้างเฉลี่ย", "บาท/เดือน", 0, highlight=list(ctx.filters.regions)), "ov_region_wage")
                if ctx.filters.regions:
                    st.caption("แท่งเข้ม = ภาคที่เลือกในตัวกรอง · ภาคอื่นจางลงเพื่อให้เทียบกันได้")
    with c2:
        with st.container(border=True, key=_ckey()):
            ok = []
            if len(sa):
                d = sa[sa["sex"].isin(["ชาย", "หญิง"]) & (sa["age_group"] != "รวม") & (sa["period_idx"] <= idx)].dropna(subset=["wage"])
                cnt = d.groupby("period_idx").size()
                ok = cnt[cnt >= 14]
            if len(ok) == 0:
                _card_title("ค่าจ้างชาย-หญิงตามกลุ่มอายุ")
                ui.empty_state("ไม่มีค่าจ้างเพศ×อายุที่ผ่านการตรวจสอบ")
            else:
                p = int(ok.index.max())
                cur = d[d["period_idx"] == p]
                ages = [a for a in ["15-19 ปี", "20-24 ปี", "25-29 ปี", "30-34 ปี", "35-39 ปี", "40-49 ปี", "50-59 ปี", "60 ปีขึ้นไป"] if a in set(cur["age_group"])]
                cur = cur.assign(age_group=pd.Categorical(cur["age_group"], ages, ordered=True)).sort_values("age_group")
                _card_title("ค่าจ้างชาย-หญิงตามกลุ่มอายุ", f"บาทต่อเดือน · {_plabel(p)}")
                _plot_inline(charts.grouped_bar(cur, "age_group", "wage", "sex", "ค่าจ้างเฉลี่ย", "บาท/เดือน", 0), "ov_sexage")


def _plot_inline(fig, key: str) -> None:
    st.plotly_chart(fig, width="stretch", key=key, config={"displayModeBar": False})


def _insights(ctx: Ctx, idx: int, r: float | None) -> list[tuple[str, str]]:
    """Up to three sentences made only of numbers that are on this page."""
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
    if r is not None:
        direction = "ตรงข้ามกัน" if r < 0 else "ไปทางเดียวกัน"
        out.append((f"ค่าจ้างกับอัตราการว่างงานเคลื่อนไหว{direction} (r = {r:.2f})", "เป็นความสัมพันธ์เชิงสถิติ ไม่ใช่เหตุและผล"))
    return out


def _province_scatter_insights(ctx: Ctx, idx: int) -> None:
    b = ctx.bundle
    p1, p2, p3 = st.columns([1.05, 1.15, 1], gap="small")
    with p1:
        with st.container(border=True, key=_ckey()):
            prov = b.get("province")
            if prov.empty:
                _card_title("จังหวัดที่อัตราการว่างงานสูงสุด")
                ui.empty_state("ไม่มีข้อมูลรายจังหวัด")
            else:
                pp = max(i for i in prov["period_idx"].unique() if i <= idx) if (prov["period_idx"] <= idx).any() else int(prov["period_idx"].max())
                f = ctx.filters
                ps = sel_.province_snapshot(b, pp, tuple(f.sexes) or ("รวม",))
                scope = " · ".join(x for x in (", ".join(f.regions), ", ".join(f.sexes)) if x)
                _card_title("จังหวัดที่อัตราการว่างงานสูงสุด", f"5 อันดับแรก · {_plabel(pp)}" + (f" · {scope}" if scope else ""))
                pdata = ps.data
                if not ps.empty and f.regions and b.has("province_region"):
                    pr = b.get("province_region")
                    inreg = set(pr[(pr["year_be"] == pp // 4) & (pr["region"].isin(f.regions))]["province"])
                    pdata = pdata[pdata["province"].isin(inreg)]
                if ps.empty or pdata.empty:
                    ui.empty_state(ps.unavailable_reason or "ไม่มีข้อมูลจังหวัดในภาคและเพศที่เลือก")
                else:
                    _plot_inline(charts.province_bar(pdata, "rate_pct", "อัตราการว่างงาน", "ร้อยละ", top=5), "ov_prov")
                    st.caption("ตัวอย่างระดับจังหวัดมีขนาดเล็ก ค่าแกว่งสูง ใช้ดูภาพรวมเท่านั้น")
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
                _plot_inline(labour_page._scatter_figure(d, "wage", "ค่าจ้างเฉลี่ย", "บาท/เดือน"), "ov_scatter")
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


def home(ctx: Ctx) -> None:

    b, f = ctx.bundle, ctx.filters
    sel = sel_.unemployed_series(b, f)
    idx = sel_.kpi_period(sel, f) if not sel.empty else None
    if idx is None:
        ui.empty_state(sel.unavailable_reason if not sel.empty and sel.unavailable_reason else "ไม่มีข้อมูลในช่วงเวลาและตัวกรองที่เลือก กรุณาขยายช่วงปีหรือกดล้างตัวกรอง")
        return
    _kpi_row(ctx, idx, sel)
    st.caption(f"ไตรมาสล่าสุดในช่วงที่เลือก: {_plabel(idx)} · การ์ดที่ค่าล่าสุดเก่ากว่านี้จะบอกไตรมาสของค่านั้นไว้เอง")
    _map_and_trend(ctx, idx, sel)
    _wage_cards(ctx, idx)
    _province_scatter_insights(ctx, idx)
    with st.expander("รายละเอียดเพิ่มเติม: แนวโน้ม 3 ตัวชี้วัดและความสัมพันธ์ (ค่าจ้างและการมีงานทำ)"):
        labour_page.national_section(ctx)
    with st.expander("เทียบกับเศรษฐกิจ (GDP)"):
        from dashboard import pages
        pages.economic(ctx)
