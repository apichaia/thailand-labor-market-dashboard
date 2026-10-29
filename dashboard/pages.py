"""The six dashboard sections. Each function receives a Ctx and renders itself."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import streamlit as st

import config
from analytics import metrics
from analytics import selectors as sel_
from dashboard import charts
from dashboard import components as ui
from data_processing import normalize as nz
from data_processing.pipeline import DataBundle

SEX_ORDER = ["ชาย", "หญิง"]


@dataclass
class Ctx:
    bundle: DataBundle
    filters: sel_.Filters
    statuses: dict = field(default_factory=dict)
    manifest: dict = field(default_factory=dict)
    ckan: dict = field(default_factory=dict)
    refresh_failures: list = field(default_factory=list)


_CARD_N = [0]


def reset_cards() -> None:
    """Call once per page render so card keys are the same on every rerun."""
    _CARD_N[0] = 0


def _ckey() -> str:
    _CARD_N[0] += 1
    return f"card_{_CARD_N[0]}"


def _plot(fig, key: str) -> None:
    """Chart without Plotly's English toolbar (hover tooltips stay in Thai)."""
    with st.container(border=True, key=f"card_plot_{key}"):
        st.plotly_chart(fig, width="stretch", key=key, config={"displayModeBar": False})


def _plabel(idx: int) -> str:
    return nz.period_label(idx // 4, idx % 4 + 1)


def _plabel_full(idx: int) -> str:
    return f"{_plabel(idx)} ({nz.period_months_th(idx % 4 + 1)} {idx // 4})"


def _src_url(key: str) -> str:
    return config.SOURCES_BY_KEY[key].landing_url


def _show_sel_notes(sel: sel_.Selection) -> None:
    for n in sel.notes:
        ui.notice("info", ui.esc(n))
    if sel.ignored:
        ui.notice("warn", "ตัวกรอง " + ui.esc(", ".join(sel.ignored)) + " ไม่มีผลกับกราฟ/ตารางนี้ เพราะแหล่งข้อมูลไม่มีมิตินี้ร่วมกัน", "ตัวกรองบางส่วนไม่ถูกใช้")


def _period_pick(label: str, idxs: list[int], key: str, default: int | None = None) -> int | None:
    """The quarter a chart shows. No widget of its own: it follows the sidebar year and ticked quarters.

    Latest quarter of the selected year that the chart's data has. When that year has none (the table starts later or
    stops earlier) the newest quarter at or before the year is used and a short line says so (nothing is invented)."""
    pool = sorted({int(i) for i in idxs})
    if not pool:
        return None
    yr = st.session_state.get("f_year")
    qs = st.session_state.get("f_quarters") or [1, 2, 3, 4]
    by_q = [i for i in pool if (i % 4 + 1) in qs] or pool
    in_year = [i for i in by_q if yr in (None, "ทุกปี") or i // 4 == yr]
    if in_year:
        return default if default in in_year else in_year[-1]
    older = [i for i in by_q if i // 4 <= yr]
    idx = older[-1] if older else by_q[0]
    st.caption(f"ปี {yr} ไม่มีข้อมูลของกราฟนี้ จึงแสดงไตรมาสที่ใกล้ที่สุด: {_plabel_full(idx)}")
    return idx


THOUSAND_COLS = ("u_k", "lf_k", "emp_k", "value_k", "unemployed_k", "yoy_abs", "qoq_abs")


def persons(df, cols=THOUSAND_COLS):
    """NSO publishes headcounts in thousands; the dashboard shows persons (x1000). Returns a copy."""
    if df is None or len(df) == 0:
        return df
    d = df.copy()
    for c in cols:
        if c in d.columns:
            d[c] = d[c] * 1000.0
    return d


CSV_COLUMNS = {
    "year_be": "ปี พ.ศ.", "quarter": "ไตรมาส", "period_idx": "ลำดับไตรมาส", "period_label": "ช่วงเวลา", "region": "ภูมิภาค",
    "region_basis": "การแบ่งภาค", "area": "เขตการปกครอง", "sex": "เพศ", "edu_group": "ระดับการศึกษา", "edu_raw": "ระดับการศึกษา (ตามต้นฉบับ)",
    "duration": "ระยะเวลาหางาน", "age_group": "กลุ่มอายุ", "status": "สถานภาพ", "category": "เหตุผล", "reason": "สาเหตุ", "cases": "จำนวนกรณี",
    "province": "จังหวัด", "u_k": "ผู้ว่างงาน (คน)", "lf_k": "กำลังแรงงาน (คน)", "emp_k": "ผู้มีงานทำ (คน)", "value_k": "ค่า (คน)",
    "rate_pct": "อัตราการว่างงาน (%)", "rate_pub_pct": "อัตราที่ สสช. เผยแพร่ (%)", "rate_calc_pct": "อัตราที่คำนวณ (%)", "rate_gap_pp": "ส่วนต่างอัตรา (จุด)",
    "unemployed_persons": "ผู้ว่างงาน (คน)", "unemployed_k": "ผู้ว่างงาน (คน)", "yoy_abs": "เทียบปีก่อน (คน)", "yoy_pct": "เทียบปีก่อน (%)",
    "qoq_abs": "เทียบไตรมาสก่อน (คน)", "qoq_pct": "เทียบไตรมาสก่อน (%)", "robust_z": "ค่า z แบบทนทาน", "significant": "ผิดปกติเชิงสถิติ",
    "quality_ok": "ผ่านการตรวจสอบ", "quality_note": "หมายเหตุคุณภาพข้อมูล", "gdp_yoy_pct": "อัตราเติบโตของ GDP เทียบปีก่อน (%)",
    "gdp_cvm_mbaht": "GDP ปริมาณลูกโซ่ (ล้านบาท)", "gdp_flag": "หมายเหตุ GDP", "year_ce": "ปี ค.ศ.", "rate_yoy_pp": "เทียบปีก่อนของอัตรา (จุด)",
    "preliminary": "ข้อมูลเบื้องต้น", "reconciled": "ผ่านการตรวจยอดรวม", "source": "แหล่งที่มา",
}


def _download(df: pd.DataFrame, name: str, key: str, label="ดาวน์โหลดข้อมูลที่กรองแล้ว (ไฟล์ .csv)") -> None:
    if df is not None and len(df):
        out = persons(df).drop(columns=[c for c in ("date", "period_idx") if c in df.columns]).rename(columns=CSV_COLUMNS)
        st.download_button(label, ui.csv_bytes(out), file_name=f"{name}.csv", mime="text/csv", key=key)


# ---------------------------------------------------------------------------
# 1. Executive overview
# ---------------------------------------------------------------------------


def _card_title(text: str, sub: str = "") -> None:
    sub_html = f'<div class="caption" style="margin:0 4px 2px 4px">{ui.esc(sub)}</div>' if sub else ""
    st.markdown(f'<div class="card-title">{ui.esc(text)}</div>{sub_html}', unsafe_allow_html=True)


REGION_MAP = st.components.v2.component("region_svg_map", css=charts.MAP_CSS, js=charts.MAP_JS)
_ALL = sel_.Filters(year_min=0, year_max=9999)


def on_map_click(key: str) -> None:
    """Runs before the rerun: clicking a region on any map sets the sidebar region filter (the whole page follows it)."""
    try:
        region = st.session_state[key]["region"]
    except Exception:
        return
    if region:
        st.session_state["f_regions"] = [region]


def show_whole_country() -> None:
    st.session_state["f_regions"] = []


def _region_map(b, f, idx: int, key: str, height: int = 300, caption: bool = True, compact: bool = False, side_legend: bool = False) -> None:
    """Clickable map of Thailand split into the five regions. A click zooms into that region and filters the page to it."""
    import functools

    measure = st.radio("ค่าที่แสดงบนแผนที่", ["อัตราการว่างงาน (%)", "ผู้ว่างงาน (คน)"], horizontal=True, key=f"{key}_measure",
                       label_visibility="collapsed")
    col, label, unit, dec = (("rate_pct", "อัตราการว่างงาน", "%", 2) if measure.startswith("อัตรา") else ("u_k", "ผู้ว่างงาน", "คน", 0))
    mp = sel_.region_map_frame(b, _ALL, idx, col)
    if mp.empty:
        ui.empty_state(mp.unavailable_reason or "ไม่มีข้อมูลสำหรับแผนที่")
        return
    zoom = [r for r in f.regions if r in set(mp.data["region"])]
    data = persons(mp.data, ("u_k", "lf_k", "value")) if col == "u_k" else mp.data
    data = data[data["region"].isin(zoom)] if zoom else data
    svg = charts.region_svg_map(b.geo, data, label, unit, dec)
    if svg is None:
        ui.empty_state("ไตรมาสนี้ไม่มีค่าให้แสดงบนแผนที่ (ไม่มีตัวหาร หรือภาคที่เลือกไม่มีข้อมูล) ไม่ประมาณค่าแทน")
        if zoom:
            st.button("← ดูทั้งประเทศ", key=f"{key}_back_empty", on_click=show_whole_country)
        return
    ckey = f"{key}_svg_" + ("|".join(zoom) if zoom else "all")
    col_map, col_key = st.columns([1.25, 1], gap="small", vertical_alignment="center")
    with col_map:
        REGION_MAP(data=svg, key=ckey, on_region_change=functools.partial(on_map_click, ckey))
    with col_key:
        st.markdown(charts.region_map_legend(data, label, unit, dec, vertical=True), unsafe_allow_html=True)
        if zoom:
            st.button("← ดูทั้งประเทศ", key=f"{key}_back", on_click=show_whole_country)
    if caption:
        st.caption(f"{_plabel(idx)} · " + ("ทั้งหน้านี้แสดงเฉพาะภาคที่เลือก" if zoom else "คลิกที่ภูมิภาคเพื่อขยายและดูเฉพาะภาคนั้น") + " · แต่ละสีคือหนึ่งภูมิภาค")


def _period_or_latest(df: pd.DataFrame, idx: int) -> int | None:
    """The KPI quarter if the table has it, otherwise the newest quarter the table has (never invented)."""
    if df is None or df.empty:
        return None
    have = set(df["period_idx"])
    return idx if idx in have else max(have)


def _go_labour_page() -> None:
    st.session_state["nav_page"] = "4 ค่าจ้างและเศรษฐกิจ"


def _labour_row(ctx: Ctx, idx: int, period: str) -> None:
    """Employment rate, wage and the latest quarter each indicator really has (they do not end together)."""
    b = ctx.bundle
    lmn = b.get("lm_national")
    if lmn.empty:
        return
    e = metrics.kpi_snapshot(lmn[["period_idx", "emp_pct"]], "emp_pct", idx)
    w = metrics.kpi_snapshot(lmn[["period_idx", "wage"]], "wage", idx)
    wage_bad = [int(i) for i in b.excluded.get("lm_wage", [])]
    c1, c2, c3 = st.columns([1, 1, 1.6], gap="small")
    if pd.isna(e["value"]):
        c1.markdown(ui.kpi_card("อัตราการมีงานทำ", None, na_reason="ไตรมาสนี้ไม่มีค่าที่เชื่อถือได้",
                                source="สสช. OS_02_0016_03"), unsafe_allow_html=True)
    else:
        yoy = ui.fmt_signed(e["yoy_abs"], 2, " จุด") if not e["yoy_reason"] else "ไม่มีข้อมูล"
        c1.markdown(ui.kpi_card("อัตราการมีงานทำ", ui.fmt_num(e["value"], 2), "%", f"เทียบปีก่อน: {yoy}", None,
                                "สสช. OS_02_0016_03 · " + period), unsafe_allow_html=True)
    if pd.isna(w["value"]):
        why = ("ไตรมาสนี้ตารางต้นทางของ สสช. ให้ค่าจ้างขัดแย้งกันเอง จึงไม่แสดง ไม่เลือกตารางใดเป็นฝ่ายถูก" if idx in wage_bad
               else "ไตรมาสนี้ไม่มีค่าจ้างที่ผ่านการตรวจสอบ")
        c2.markdown(ui.kpi_card("ค่าจ้างเฉลี่ยของลูกจ้าง", None, na_reason="ไตรมาสนี้ไม่มีค่าจ้างที่เชื่อถือได้", source=why), unsafe_allow_html=True)
    else:
        yoy = ui.fmt_signed(w["yoy_pct"], 1, "%") if not w["yoy_reason"] else "ไม่มีข้อมูล"
        c2.markdown(ui.kpi_card("ค่าจ้างเฉลี่ยของลูกจ้าง", ui.fmt_num(w["value"], 0), "บาท/เดือน", f"เทียบปีก่อน: {yoy}",
                                None, "สสช. OS_02_0024_01 · " + period), unsafe_allow_html=True)

    def last(df, col):
        d = df.dropna(subset=[col]) if len(df) else df
        return None if len(d) == 0 else int(d["period_idx"].max())

    nat = b.get("national")
    emp_nat = b.get("lm_employed_national")
    gdp = b.get("gdp")
    rows = [("จำนวนผู้ว่างงาน", last(nat, "u_k"), ""), ("อัตราการว่างงาน (ผ่านการตรวจ)", last(nat, "rate_pct"), ""),
            ("อัตรามีงานทำ", last(lmn, "emp_pct"), ""),
            ("ค่าจ้างเฉลี่ย (ผ่านการตรวจ)", last(lmn, "wage"), f"เว้น {len(wage_bad)} ไตรมาส" if wage_bad else ""),
            ("จำนวนผู้มีงานทำ (สสช. OS_02_0002_01)", last(emp_nat, "emp_k"), "" if len(emp_nat) else ""),
            ("GDP เติบโต", last(gdp, "gdp_yoy_pct"), "")]
    body = "".join(f'<div><span class="k">{ui.esc(k)}:</span> <b>{ui.esc(_plabel(i) if i is not None else "—")}</b>'
                   + (f' <span class="muted">({ui.esc(note)})</span>' if note else "") + "</div>" for k, i, note in rows)
    c3.markdown(f'<div class="card"><div class="kpi-label">ข้อมูลล่าสุดที่มีค่าจริงของแต่ละตัวชี้วัด {ui.info("freshness")}</div>'
                f'<div class="kpi-stats" style="margin-top:8px">{body}</div>'
                f'</div>', unsafe_allow_html=True)
    st.button("ดูรายละเอียดอัตรามีงานทำและค่าจ้าง →", on_click=_go_labour_page, key="ov_to_labour")


def demographic_notice() -> None:
    ui.notice("warn", "จำนวนผู้ว่างงานของกลุ่มที่ใหญ่กว่าย่อมมากกว่าโดยธรรมชาติ <b>ห้ามสรุปว่ากลุ่มใดเสี่ยงสูงจากจำนวนคนเพียงอย่างเดียว</b> "
                      "ให้ดูอัตราการว่างงาน (เทียบกับกำลังแรงงานของกลุ่มนั้น) ควบคู่กันเสมอ", "การตีความ")


def demographic(ctx: Ctx) -> None:
    b, f = ctx.bundle, ctx.filters
    ui.section_title("การวิเคราะห์จำแนกตามลักษณะประชากร")
    demographic_notice()
    sub = st.radio("หมวด", ["ระดับการศึกษา", "เพศ", "กลุ่มอายุ"], horizontal=True, key="nav_demo", label_visibility="collapsed")
    if sub == "ระดับการศึกษา":
        _edu_tab(b, f)
    elif sub == "เพศ":
        _sex_tab(b, f)
    else:
        _age_tab(b, f)


def _edu_tab(b, f):
    cnt = sel_.breakdown_education(b, f)
    if cnt.empty:
        ui.empty_state(cnt.unavailable_reason or "ไม่มีข้อมูลในช่วงที่เลือก")
        return
    rates = sel_.education_rates(b, f)
    idxs = sorted(cnt.data["period_idx"].unique())
    idx = _period_pick("ไตรมาสที่แสดงในกราฟแท่งและตาราง", idxs, "edu_period")
    d = cnt.data[cnt.data["period_idx"] == idx]
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("**จำนวนผู้ว่างงาน**")
        _plot(charts.hbar_education(persons(d), "u_k", nz.EDU_ORDER, "จำนวนผู้ว่างงาน", "คน", 0), "edu_bar_cnt")
    with c2:
        st.markdown("**อัตราการว่างงานของแต่ละระดับการศึกษา**")
        if rates.empty:
            ui.empty_state(rates.unavailable_reason or "ข้อมูลไม่เพียงพอสำหรับคำนวณอัตรา")
        else:
            rd = rates.data[rates.data["period_idx"] == idx]
            if rd.empty:
                ui.empty_state("ไม่มีอัตราการว่างงานรายระดับการศึกษาในไตรมาสนี้ (เริ่ม ไตรมาส 1/2563)")
            else:
                _plot(charts.hbar_education(rd, "rate_pct", nz.EDU_ORDER, "อัตราการว่างงาน", "ร้อยละ", 2), "edu_bar_rate")
    ui.chart_caption(cnt.source, _plabel_full(idx), "คน / ร้อยละ", "อัตรา = ผู้ว่างงาน ÷ (ผู้ว่างงาน + ผู้มีงานทำ) ของระดับการศึกษานั้น",
                     "จัดกลุ่มระดับการศึกษาเป็น 6 กลุ่มหยาบ เพราะ สสช. เปลี่ยนชื่อสายการศึกษาบางสายระหว่างปี ตัวหารไม่รวมผู้รอฤดูกาล จึงต่างจากอัตรา สสช. ไม่เกินราว 0.05 จุด",
                     _src_url("nso_u_edu"))
    _show_sel_notes(cnt)

    st.markdown("**แนวโน้มแยกตามกลุ่มการศึกษา**")
    mode = st.radio("แสดง", ["จำนวน (คน)", "อัตรา (%)"], horizontal=True, key="edu_trend_mode")
    tf = f   # only the picked years and quarters
    cnt_t, rates_t = sel_.breakdown_education(b, tf), sel_.education_rates(b, tf)
    if mode.startswith("จำนวน"):
        tr = persons(cnt_t.data)
        fig = charts.multi_line(tr, "u_k", "edu_group", "จำนวนผู้ว่างงาน", "คน", 0, focus=f.focus)
    elif not rates_t.empty:
        tr = rates_t.data
        fig = charts.multi_line(tr, "rate_pct", "edu_group", "อัตราการว่างงาน", "ร้อยละ", 2, focus=f.focus)
    else:
        ui.empty_state(rates.unavailable_reason or "ไม่มีอัตรา")
        fig = None
    if fig is not None and len(tr) > 1:
        _plot(fig, "edu_trend")
        ui.chart_caption(cnt.source if mode.startswith("จำนวน") else rates.source, ui.period_range_text(tr), "คน / ร้อยละ")

    ui.section_title("ตารางสรุปรายระดับการศึกษา")
    tbl = persons(d)[["edu_group", "u_k"]].copy()
    tbl["สัดส่วนของผู้ว่างงานทั้งหมด (%)"] = tbl["u_k"] / tbl["u_k"].sum() * 100
    if not rates.empty:
        rr = rates.data[rates.data["period_idx"] == idx][["edu_group", "rate_pct"]]
        tbl = tbl.merge(rr, on="edu_group", how="left")
    else:
        tbl["rate_pct"] = np.nan
    tbl = tbl.rename(columns={"edu_group": "ระดับการศึกษา", "u_k": "ผู้ว่างงาน (คน)", "rate_pct": "อัตราการว่างงาน (%)"})
    st.dataframe(tbl, width="stretch", hide_index=True, column_config={
        "ผู้ว่างงาน (คน)": st.column_config.NumberColumn(format="localized"),
        "สัดส่วนของผู้ว่างงานทั้งหมด (%)": st.column_config.NumberColumn(format="%.1f"),
        "อัตราการว่างงาน (%)": st.column_config.NumberColumn(format="%.2f")})
    _download(cnt.data.merge(rates.data[["period_idx", "edu_group", "rate_pct"]], on=["period_idx", "edu_group"], how="left") if not rates.empty else cnt.data,
              "unemployment_by_education", "dl_edu")


def _sex_tab(b, f):
    cnt = sel_.breakdown_sex(b, f)
    if cnt.empty:
        ui.empty_state(cnt.unavailable_reason or "ไม่มีข้อมูลในช่วงที่เลือก")
        return
    last_n = st.slider("จำนวนไตรมาสล่าสุดที่แสดงในกราฟแท่งกลุ่ม", 4, 16, 8, key="sex_n")
    idxs = sorted(cnt.data["period_idx"].unique())[-last_n:]
    d = cnt.data[cnt.data["period_idx"].isin(idxs)]
    _plot(charts.grouped_bar(persons(d), "period_label", "u_k", "sex", "จำนวนผู้ว่างงาน", "คน", 0), "sex_bar")
    ui.chart_caption(cnt.source, ui.period_range_text(d), "คน", "ผลรวมของแถวที่ตรวจสอบยอดรวมกับตารางอ้างอิงแล้ว (ไม่นำแถว 'รวม' มาบวกซ้ำ)",
                     "ไตรมาสที่ตรวจสอบไม่ผ่านถูกยกเว้นและเว้นว่าง", _src_url("nso_u_province"))
    _show_sel_notes(cnt)
    ui.section_title("ตารางผู้ว่างงานรายเพศ")
    tbl = persons(d).pivot_table(index="period_label", columns="sex", values="u_k", aggfunc="sum").reset_index().rename(columns={"period_label": "ไตรมาส"})
    st.dataframe(tbl, width="stretch", hide_index=True)
    _download(cnt.data, "unemployment_by_sex", "dl_sex")


def _age_tab(b, f):
    ag = sel_.age_breakdown(b, f)
    if ag.empty:
        ui.empty_state(ag.unavailable_reason or "ไม่มีข้อมูลกลุ่มอายุ")
        return
    _show_sel_notes(ag)
    idxs = sorted(ag.data["period_idx"].unique())
    idx = _period_pick("ไตรมาสที่แสดง", idxs, "age_period")
    d = persons(ag.data[ag.data["period_idx"] == idx]).pivot_table(index="age_group", columns="status", values="u_k", aggfunc="sum").reset_index()
    order = ["15-19 ปี", "20-24 ปี", "25-29 ปี", "30-34 ปี", "35-39 ปี", "40-49 ปี", "50-59 ปี", "60 ปีขึ้นไป"]
    d["age_group"] = pd.Categorical(d["age_group"], categories=order, ordered=True)
    d = d.sort_values("age_group")
    import plotly.graph_objects as go
    fig = go.Figure()
    for i, col in enumerate([c for c in d.columns if c != "age_group"]):
        fig.add_trace(go.Bar(x=[a_.replace(" ", "<br>") for a_ in d["age_group"].astype(str)], y=d[col], name=col,
                             customdata=d["age_group"].astype(str), marker_color=[charts.theme.PRIMARY, charts.theme.ACCENT][i % 2],
                             hovertemplate="<b>%{customdata}</b><br>" + col + ": %{y:,.0f} คน<extra></extra>"))
    fig.update_layout(barmode="stack")
    charts.style(fig, ytitle="จำนวนผู้ว่างงาน (คน)", height=380)
    _plot(fig, "age_bar")
    ui.chart_caption(ag.source, _plabel_full(idx), "คน", "แยกตามสถานภาพแรงงาน: หางานทำ / ไม่หางานทำแต่พร้อมทำงาน (รวมสองส่วนเท่ากับผู้ว่างงาน)",
                     "ตัวกรองเพศและการศึกษาไม่มีผลในกราฟนี้", _src_url("nso_u_age_status"))
    pr = sel_.published_age_rates(b, f)
    st.markdown("**อัตราการว่างงานรายกลุ่มอายุ (ตามที่ สสช. เผยแพร่)**")
    if pr.empty or idx not in set(pr.data["period_idx"]):
        ui.empty_state((pr.unavailable_reason if pr.empty else None) or "ไม่มีอัตรารายกลุ่มอายุที่ สสช. เผยแพร่ในไตรมาสนี้")
    else:
        rd = pr.data[pr.data["period_idx"] == idx].copy()
        rd["age_group"] = pd.Categorical(rd["age_group"], categories=order, ordered=True)
        rd = rd.sort_values("age_group")
        fig2 = go.Figure(go.Bar(x=[a_.replace(" ", "<br>") for a_ in rd["age_group"].astype(str)], y=rd["rate_pct"],
                                customdata=rd["age_group"].astype(str), marker_color=charts.theme.MIDBLUE,
                                hovertemplate="<b>%{customdata}</b><br>อัตราการว่างงาน: %{y:.2f} ร้อยละ<extra></extra>"))
        charts.style(fig2, ytitle="อัตราการว่างงาน (ร้อยละ)", height=340, legend_bottom=False)
        _plot(fig2, "age_rate")
        ui.chart_caption(pr.source, _plabel_full(idx), "ร้อยละ", "ตามที่ สสช. เผยแพร่ (ไม่ได้คำนวณใหม่)", "ระดับประเทศ ไม่ขึ้นกับตัวกรองเพศ/ภาค", _src_url("nso_rate_new"))
    _download(ag.data, "unemployment_by_age", "dl_age")


# ---------------------------------------------------------------------------
# 3. Regional analysis
# ---------------------------------------------------------------------------


def regional(ctx: Ctx) -> None:
    b, f = ctx.bundle, ctx.filters
    ui.section_title("เปรียบเทียบรายภูมิภาค", "region_break")
    tr = sel_.region_trend(b, f)
    if tr.empty:
        ui.empty_state(tr.unavailable_reason or "ไม่มีข้อมูลภูมิภาค")
        return
    ui.notice("info", "ชุดข้อมูลหลักมีระดับภาค แผนที่ด้านบนจึงระบายสีตามภาค (ไม่ใช่ค่ารายจังหวัด) ส่วนรายจังหวัดมีเฉพาะตารางผู้ว่างงานรายจังหวัดของ สสช. (ปี 2564 เป็นต้นไป) ซึ่งแสดงด้านล่างเป็นแท่งและตาราง "
                      "ตั้งแต่ปี 2568 สสช. แยกภาคตะวันออกและใต้ชายแดน แดชบอร์ดรวมกลับเป็น 5 ภาคเพื่อให้เทียบข้ามช่วงได้")
    _show_sel_notes(tr)
    idxs = sorted(tr.data["period_idx"].unique())
    idx = _period_pick("ไตรมาสที่เปรียบเทียบ", idxs, "reg_period")
    snap = tr.data[tr.data["period_idx"] == idx]
    with st.container(border=True, key=_ckey()):
        st.markdown("**แผนที่ประเทศไทยแบ่งตามภูมิภาค**")
        _region_map(b, f, idx, "reg_map", height=430)
    ui.chart_caption("ขอบเขตจังหวัด geoBoundaries (ODbL 1.0, ข้อมูลจาก OpenStreetMap) · ภาคของแต่ละจังหวัด สสช. (ST_02_2005005_4) · ค่า สสช. (OS_02_0003_01, OS_02_0001_01)",
                     _plabel_full(idx), "ร้อยละ / คน",
                     "แต่ละสีคือหนึ่งภูมิภาค ตัวเลขของภาคอยู่ในคำอธิบายสีข้างแผนที่ (เรียงจากค่ามากไปน้อย) และเมื่อชี้ที่จังหวัด; อัตรา = ผู้ว่างงานของภาค ÷ กำลังแรงงานของภาค × 100",
                     "ไม่ใช่ข้อมูลรายจังหวัด (ดูรายจังหวัดด้านล่าง); มีเฉพาะปี 2563 เป็นต้นไป; ปี 2568 รวม 7 ภาคกลับเป็น 5 ภาค; ภาคที่ไม่มีค่าเป็นสีเทา",
                     "https://www.geoboundaries.org/")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("**จำนวนผู้ว่างงาน**")
        _plot(charts.region_bar(persons(snap), "u_k", "จำนวนผู้ว่างงาน", "คน", 0), "reg_bar_u")
    with c2:
        st.markdown("**อัตราการว่างงาน**")
        rs = snap.dropna(subset=["rate_pct"])
        if rs.empty:
            ui.empty_state("ไตรมาสนี้ไม่มีอัตราการว่างงานรายภาค (ไม่มีตัวหารหรือไม่ผ่านการตรวจสอบ)")
        else:
            _plot(charts.region_bar(rs, "rate_pct", "อัตราการว่างงาน", "ร้อยละ", 2), "reg_bar_r")
    ui.chart_caption(tr.source, _plabel_full(idx), "คน / ร้อยละ", "อัตรา = ผู้ว่างงานของภาค ÷ กำลังแรงงานของภาคเดียวกัน × 100",
                     "ภาคที่มีประชากรมากย่อมมีจำนวนผู้ว่างงานมากกว่า ให้เทียบด้วยอัตรา; ข้อมูลภาคจากการสำรวจตัวอย่างมีความคลาดเคลื่อนจากการสุ่ม", _src_url("nso_u_region"))

    st.markdown("**แนวโน้มแยกตามภูมิภาค**")
    mode = st.radio("แสดง", ["จำนวน (คน)", "อัตรา (%)"], horizontal=True, key="reg_trend_mode")
    col, ttl, unit = ("u_k", "จำนวนผู้ว่างงาน", "คน") if mode.startswith("จำนวน") else ("rate_pct", "อัตราการว่างงาน", "ร้อยละ")
    td = persons(sel_.region_trend(b, f).data)   # only the picked years and quarters
    td["series"] = td["region"]
    if td[col].notna().sum() > 1:
        cf = (b.availability.get("conflicts") or {}).get("rate", []) if col == "rate_pct" else []
        lo_t, hi_t = int(td["period_idx"].min()), int(td["period_idx"].max())
        _plot(charts.multi_line(td, col, "series", ttl, unit, 0 if col == "u_k" else 2, focus=f.focus,
                                excluded=[r["period_idx"] for r in cf if lo_t <= r["period_idx"] <= hi_t]), "reg_trend")
        ui.conflict_box(cf, _plabel, lo_t, hi_t, " ของอัตราการว่างงาน")
        ui.chart_caption(tr.source, ui.period_range_text(td), unit, "ดูคำอธิบายด้านบน",
                         "ตั้งแต่ปี 2568 ภาคกลางรวมภาคตะวันออก และภาคใต้รวมใต้ชายแดน เพื่อให้เส้นต่อเนื่อง (จังหวัดชุดเดียวกัน)", _src_url("nso_u_region"))
    else:
        ui.empty_state("ข้อมูลไม่เพียงพอสำหรับแสดงแนวโน้มรายภาคในช่วงที่เลือก")

    ui.section_title("ตารางรายละเอียดรายภูมิภาค")
    tbl = persons(tr.data)[["period_label", "region", "region_basis", "u_k", "lf_k", "rate_pct"]].rename(columns={
        "period_label": "ไตรมาส", "region": "ภูมิภาค", "region_basis": "การแบ่งภาค", "u_k": "ผู้ว่างงาน (คน)",
        "lf_k": "กำลังแรงงาน (คน)", "rate_pct": "อัตราการว่างงาน (%)"})
    q = st.text_input("ค้นหาภูมิภาค/ไตรมาสในตาราง", key="reg_search")
    if q:
        tbl = tbl[tbl.apply(lambda r: q in " ".join(map(str, r.values)), axis=1)]
    st.dataframe(tbl, width="stretch", hide_index=True, column_config={
        "ผู้ว่างงาน (คน)": st.column_config.NumberColumn(format="localized"), "กำลังแรงงาน (คน)": st.column_config.NumberColumn(format="localized"),
        "อัตราการว่างงาน (%)": st.column_config.NumberColumn(format="%.2f")})
    _download(tr.data, "unemployment_by_region", "dl_reg")

    ui.section_title("รายจังหวัด (ข้อมูลสำรวจตัวอย่าง ปี 2564 เป็นต้นไป)")
    prov = b.get("province")
    if prov.empty:
        ui.empty_state("ไม่มีข้อมูลรายจังหวัดที่ผ่านการตรวจสอบ")
        return
    pidx = _period_pick("ไตรมาส (รายจังหวัด)", sorted(prov["period_idx"].unique()), "prov_period")
    sx = st.radio("เพศ", ["รวม", "ชาย", "หญิง"], horizontal=True, key="prov_sex")
    ps = sel_.province_snapshot(b, pidx, (sx,))
    if ps.empty:
        ui.empty_state(ps.unavailable_reason)
        return
    ui.chart_caption(ps.source, _plabel_full(pidx), "ร้อยละ", "ตามที่ สสช. เผยแพร่",
                     "ตัวอย่างระดับจังหวัดมีขนาดเล็ก ค่าแกว่งจากการสุ่มสูง ไม่ควรใช้จัดอันดับจังหวัดเพียงไตรมาสเดียว; จึงแสดงเป็นตาราง ส่วนแผนที่ใช้ค่ารายภาค",
                     _src_url("nso_u_province"))
    pt = ps.data[["province", "unemployed_persons", "rate_pct"]].rename(columns={"province": "จังหวัด", "unemployed_persons": "ผู้ว่างงาน (คน)", "rate_pct": "อัตราการว่างงาน (%)"})
    pq = st.text_input("ค้นหาจังหวัด", key="prov_search")
    if pq:
        pt = pt[pt["จังหวัด"].str.contains(pq, na=False)]
    st.dataframe(pt.sort_values("อัตราการว่างงาน (%)", ascending=False), width="stretch", hide_index=True, column_config={
        "ผู้ว่างงาน (คน)": st.column_config.NumberColumn(format="%d"), "อัตราการว่างงาน (%)": st.column_config.NumberColumn(format="%.2f")})
    _download(ps.data, "unemployment_by_province", "dl_prov")


# ---------------------------------------------------------------------------
# 4. Economic context
# ---------------------------------------------------------------------------


def economic(ctx: Ctx) -> None:
    b, f = ctx.bundle, ctx.filters
    ui.section_title("การว่างงานกับภาวะเศรษฐกิจ", "gdp")
    if f.region_active(sel_.all_regions(b)) or f.sex_active or f.edu_active:
        ui.notice("warn", "GDP เป็นข้อมูลระดับประเทศ หน้านี้จึงใช้อัตราการว่างงานระดับประเทศ และไม่ใช้ตัวกรองภาค/เพศ/การศึกษา", "ตัวกรองบางส่วนไม่ถูกใช้")
    df, notes = sel_.economic_frame(b, f)
    if df.empty:
        ui.empty_state("; ".join(notes) or "ไม่มีช่วงเวลาที่ตรงกันระหว่างข้อมูลการว่างงานและ GDP ในช่วงที่เลือก")
        return
    gdp_last = int(b.get("gdp")["period_idx"].max())
    nat_last = int(b.get("national")["period_idx"].max())
    ui.notice("info", f"ทั้งสองชุดเป็นข้อมูลรายไตรมาสและจับคู่ด้วยปี+ไตรมาส (GDP เป็น ค.ศ. แปลงเป็น พ.ศ. หลังตรวจรูปแบบปีแล้ว) "
                      f"ช่วงที่ซ้อนกัน: {ui.esc(ui.period_range_text(df))}. GDP ล่าสุดที่มี: {ui.esc(_plabel(gdp_last))}"
                      + (f" ส่วนการว่างงานล่าสุด {ui.esc(_plabel(nat_last))} — ไตรมาสหลัง GDP ล่าสุดจึงไม่ถูกจับคู่ ไม่มีการประมาณค่า" if nat_last > gdp_last else ""))
    _plot(charts.two_panel(df), "eco_two")
    ui.chart_caption("สสช. (อัตราการว่างงาน) และ สศช. สศช. (GDP ปริมาณลูกโซ่, ชุดไม่ปรับฤดูกาล)", ui.period_range_text(df), "ร้อยละ / ร้อยละ เทียบปีก่อน",
                     "อัตราการว่างงาน = ผู้ว่างงาน ÷ กำลังแรงงาน; อัตราเติบโตของ GDP = ตามที่ สศช. เผยแพร่ (เทียบปีก่อน ของ GDP ราคาคงที่ ปีอ้างอิง 2545 ซึ่งตรงกับที่คำนวณจากระดับ ปริมาณลูกโซ่)",
                     "แสดงเป็นสองกราฟบนแกนไตรมาสเดียวกัน ไม่ใช้แกน y ร่วมเพราะหน่วยต่างกัน", _src_url("nesdc_gdp"))

    st.markdown("**สำรวจความสัมพันธ์ (แผนภาพการกระจาย)**")
    c1, c2 = st.columns(2)
    ymode = c1.radio("ตัวแปรการว่างงาน", ["ระดับอัตราการว่างงาน (%)", "การเปลี่ยนแปลง เทียบปีก่อน ของอัตรา (จุดร้อยละ)"], key="eco_y")
    drop_covid = c2.checkbox("ตัดไตรมาสปี 2563–2564 ออก (ทดสอบความไวของผล)", value=False, key="eco_covid")
    d = df[~df["year_be"].isin([2563, 2564])] if drop_covid else df
    ycol, ytitle, yunit = ("rate_pct", "อัตราการว่างงาน", "ร้อยละ") if ymode.startswith("ระดับ") else ("rate_yoy_pp", "เปลี่ยนแปลง เทียบปีก่อน ของอัตรา", "จุดร้อยละ")
    cs = metrics.correlation_summary(d["gdp_yoy_pct"], d[ycol])
    if cs["reason"]:
        ui.empty_state(cs["reason"])
    else:
        _plot(charts.scatter_gdp(d, "gdp_yoy_pct", ycol, ytitle, yunit), "eco_sc")
        m1, m2, m3 = st.columns(3)
        m1.metric("สหสัมพันธ์เพียร์สัน (r)", f"{cs['pearson']:.2f}", help=f"ช่วงความเชื่อมั่น 95% โดยประมาณ (การแปลงฟิชเชอร์): {cs['ci_low']:.2f} ถึง {cs['ci_high']:.2f}")
        m2.metric("สหสัมพันธ์สเปียร์แมน (ρ)", f"{cs['spearman']:.2f}", help="สหสัมพันธ์เชิงอันดับ ทนต่อค่าสุดโต่งมากกว่า เพียร์สัน")
        m3.metric("จำนวนไตรมาสที่ใช้ (n)", f"{cs['n']}")
        if abs(cs["pearson"] - cs["spearman"]) > 0.25:
            ui.notice("warn", "สหสัมพันธ์เพียร์สันกับสเปียร์แมนต่างกันมาก แสดงว่าผลถูกกำหนดโดยไม่กี่จุดสุดโต่ง (เช่น ช่วงที่เศรษฐกิจผันผวนรุนแรง) ควรตีความด้วยความระมัดระวัง")
    ui.notice("info", "ค่าสหสัมพันธ์บอกเพียงว่าตัวเลขสองชุดเคลื่อนไหวสัมพันธ์กันหรือไม่ <b>ไม่ได้พิสูจน์ว่า GDP เป็นสาเหตุของการว่างงาน</b> "
                      "ไตรมาสที่อัตราการว่างงานไม่ผ่านการตรวจสอบความสอดคล้องถูกตัดออกจากการคำนวณ", "สหสัมพันธ์ไม่ใช่ความเป็นเหตุเป็นผล")
    ui.section_title("ตารางข้อมูลที่ใช้เปรียบเทียบ")
    t = persons(df)[["period_label", "u_k", "rate_pct", "rate_yoy_pp", "gdp_yoy_pct", "gdp_flag"]].rename(columns={
        "period_label": "ไตรมาส", "u_k": "ผู้ว่างงาน (คน)", "rate_pct": "อัตราการว่างงาน (%)", "rate_yoy_pp": "เทียบปีก่อน ของอัตรา (จุด)",
        "gdp_yoy_pct": "อัตราเติบโตของ GDP เทียบปีก่อน (%)", "gdp_flag": "หมายเหตุ GDP (r=ปรับปรุง, p=เบื้องต้น)"})
    st.dataframe(t, width="stretch", hide_index=True, column_config={
        "ผู้ว่างงาน (คน)": st.column_config.NumberColumn(format="localized"), "อัตราการว่างงาน (%)": st.column_config.NumberColumn(format="%.2f"),
        "เทียบปีก่อน ของอัตรา (จุด)": st.column_config.NumberColumn(format="%+.2f"), "อัตราเติบโตของ GDP เทียบปีก่อน (%)": st.column_config.NumberColumn(format="%.1f")})
    _download(df, "unemployment_vs_gdp", "dl_eco")


# ---------------------------------------------------------------------------
# 5. Factors and evidence
# ---------------------------------------------------------------------------


def factors(ctx: Ctx) -> None:
    b, f = ctx.bundle, ctx.filters
    ui.section_title("ปัจจัยและหลักฐานที่เกี่ยวข้องกับการว่างงาน", "corr")
    ui.notice("info", "ส่วนนี้แยกหลักฐานเป็น 3 ระดับ: (A) วัดโดยตรง (B) ตัวแทน/ตัวแทน (C) สมมติฐานที่ยังไม่มีข้อมูลเพียงพอ "
                      "<b>ชุดข้อมูลตัวเลขหลักไม่มีตัวแปรที่ระบุสาเหตุการว่างงานโดยตรงสำหรับผู้ว่างงานทั้งประเทศ</b> จึงไม่สร้างกราฟสาเหตุขึ้นเอง")
    labels = ["A. หลักฐานที่วัดได้โดยตรง", "B. ตัวแทน", "C. สมมติฐานที่ต้องการหลักฐานเพิ่ม"]
    sub = st.radio("หมวดหลักฐาน", labels, horizontal=True, key="nav_factors", label_visibility="collapsed")
    if sub == labels[0]:
        bot = b.get("bot_reasons")
        st.markdown("**เหตุผลที่ผู้ว่างงานที่เคยทำงานออกจากงานเดิม**")
        if bot.empty:
            ui.empty_state("ไม่สามารถอ่านข้อมูลเหตุผลที่ออกจากงานจาก ธปท. ได้ในขณะนี้ — " + (b.availability.get("bot_reasons", {}).get("reason") or ""))
        else:
            cats = bot[bot["category"] != "ผู้ว่างงานที่เคยทำงาน"]
            win = sel_.in_time(cats, f)
            if win.empty:
                ui.empty_state(f"ข้อมูลเหตุผลที่ออกจากงานครอบคลุม {ui.period_range_text(cats)} ซึ่งไม่ทับกับช่วงเวลาที่เลือก (ขยายช่วงปีเพื่อดู)")
            else:
                _plot(charts.stacked_reasons(win), "bot_stack")
                last = int(bot["period_idx"].max())
                ui.chart_caption("ธปท. EC_RL_019 (ที่มา: สสช. สำรวจภาวะการทำงานของประชากร)", ui.period_range_text(win), "คน",
                                 "ผลรวมของ 7 เหตุผล ตรวจแล้วเท่ากับ 'ผู้ว่างงานที่เคยทำงาน' ทุกไตรมาส",
                                 f"ครอบคลุมเฉพาะผู้ที่เคยทำงาน ไม่รวมผู้เข้าสู่ตลาดแรงงานครั้งแรก; ชุดข้อมูลสิ้นสุดที่ {_plabel(last)} (ไม่ได้อัปเดตต่อ) "
                                 "ป้ายกำกับบางเหตุผลคล้ายกัน (เช่น 'หมดสัญญาจ้างแรงงาน' กับ 'หมดสัญญาจ้างงาน') ให้ดูตามชื่อในต้นฉบับ",
                                 config.SOURCES_BY_KEY["bot_reasons"].landing_url)
                ui.notice("warn", "ตัวเลขนี้บอก <b>เหตุผลที่ออกจากงานเดิม</b> ตามที่ผู้ตอบแบบสำรวจรายงาน ไม่ได้อธิบายว่าเหตุใดเศรษฐกิจโดยรวมจึงมีคนว่างงานมากหรือน้อย", "ข้อจำกัด")
                piv = win.pivot_table(index="period_label", columns="category", values="value_k", aggfunc="sum")
                share = (piv.div(piv.sum(axis=1), axis=0) * 100).round(1).reset_index().rename(columns={"period_label": "ไตรมาส"})
                st.markdown("**สัดส่วนแต่ละเหตุผล (% ของผู้ว่างงานที่เคยทำงาน)**")
                st.dataframe(share, width="stretch", hide_index=True)
                _download(win, "unemployment_reasons_bot", "dl_bot")
        st.markdown("**ระยะเวลาที่หางานทำ (ผู้ว่างงานจำแนกตามระยะเวลาหางาน)**")
        cube = b.get("cube")
        if cube.empty:
            ui.empty_state("ไม่มีตารางข้ามมิติที่ผ่านการตรวจสอบ")
        else:
            c = cube
            if f.region_active(sel_.all_regions(b)):
                c = c[c["region"].isin(f.regions)]
            if f.sex_active:
                c = c[c["sex"].isin(f.sexes)]
            if f.edu_active:
                c = c[c["edu_group"].isin(f.edus)]
            c = sel_.in_time(c, f)
            c = c[c["duration"].isin(["น้อยกว่า 1 เดือน", "1-2.9 เดือน", "3-5.9 เดือน", "6-8.9 เดือน", "9-11.9 เดือน", "12 เดือนขึ้นไป"])]
            if c.empty:
                ui.empty_state("ไม่มีข้อมูลระยะเวลาหางานในช่วงและตัวกรองที่เลือก")
            else:
                order = ["น้อยกว่า 1 เดือน", "1-2.9 เดือน", "3-5.9 เดือน", "6-8.9 เดือน", "9-11.9 เดือน", "12 เดือนขึ้นไป"]
                g = c.groupby("duration")["value_k"].sum().reindex(order).reset_index()
                g["สัดส่วน (%)"] = g["value_k"] / g["value_k"].sum() * 100
                import plotly.graph_objects as go
                fig = go.Figure(go.Bar(x=[d_.replace(" ", "<br>", 1) for d_ in g["duration"]], y=g["สัดส่วน (%)"], marker_color=charts.theme.PRIMARY,
                                       customdata=g["duration"], hovertemplate="<b>%{customdata}</b><br>สัดส่วน: %{y:.1f}%<extra></extra>"))
                charts.style(fig, ytitle="สัดส่วนของผู้ว่างงาน (ร้อยละ)", height=340, legend_bottom=False)
                _plot(fig, "dur_bar")
                ui.chart_caption("สสช. OS_02_0003_02 (ตารางข้ามมิติ)", ui.period_range_text(c), "ร้อยละของผลรวมจำนวนคนทุกไตรมาสที่เลือก",
                                 "สัดส่วนจากผลรวมของผู้ว่างงานทุกไตรมาสในช่วงที่เลือก", "เป็นผลรวมสะสมหลายไตรมาส ไม่ใช่จำนวนคนเฉพาะ; ไตรมาสที่ตรวจยอดรวมไม่ผ่านถูกยกเว้น",
                                 _src_url("nso_u_cube"))
    elif sub == labels[1]:
        ui.notice("warn", ui.esc(ui.GLOSSARY["proxy"]) + " ข้อมูลของสำนักงานประกันสังคมครอบคลุมเฉพาะผู้ประกันตนมาตรา 33 และ 39 ที่ใช้สิทธิกรณีว่างงาน "
                          "<b>ไม่ใช่ประชากรว่างงานทั้งประเทศ</b> และนับเป็น 'กรณีที่ใช้สิทธิ' ไม่ใช่จำนวนคน จึงห้ามเทียบกับจำนวนผู้ว่างงานของ สสช. โดยตรง", "ตัวแทน")
        sso = b.get("sso")
        if sso.empty:
            ui.empty_state("ไม่สามารถอ่านข้อมูลผู้ใช้สิทธิว่างงานของสำนักงานประกันสังคมได้ในขณะนี้")
        else:
            _plot(charts.sso_bar(sso), "sso_bar")
            ui.chart_caption("สำนักงานประกันสังคม (ตารางที่ 12)", f"ปี {int(sso['year_be'].min())}–{int(sso['year_be'].max())}", "กรณีที่ใช้สิทธิ",
                             "ตามที่ สำนักงานประกันสังคม เผยแพร่ แยกสาเหตุ: ถูกเลิกจ้าง / สมัครใจลาออก / สิ้นสุดสัญญาจ้าง",
                             "รายปี ผู้ประกันตน ม.33/39 เท่านั้น; ไม่ใช้ข้อมูลสาเหตุนี้กับประชากรทั้งประเทศ; ไม่มีข้อมูลปีหลัง 2565 ในไฟล์ที่เผยแพร่",
                             config.SOURCES_BY_KEY["sso_benefit"].landing_url)
            tbl = sso.pivot_table(index="year_be", columns="reason", values="cases", aggfunc="sum").reset_index().rename(columns={"year_be": "ปี พ.ศ."})
            st.dataframe(tbl, width="stretch", hide_index=True)
            _download(sso, "sso_unemployment_benefit_by_reason", "dl_sso")
    else:
        ui.notice("warn", "รายการต่อไปนี้เป็น <b>สมมติฐาน</b> ที่ข้อมูลในโปรเจกต์นี้ยังไม่พิสูจน์ ไม่ใช่ข้อเท็จจริง", "ห้ามตีความเป็นข้อสรุป")
        hyp = pd.DataFrame([
            ["ผลกระทบของเทคโนโลยีอัตโนมัติ/AI ต่อการจ้างงาน", "ข้อมูลระดับอาชีพหรือทักษะรายไตรมาสที่เชื่อมกับการลดตำแหน่งงาน", "ไม่พบข้อมูลสาธารณะที่ตรวจสอบได้และเข้าถึงอัตโนมัติ"],
            ["ทักษะไม่ตรงกับความต้องการงาน (Skills mismatch)", "ตำแหน่งงานว่างแยกทักษะ/สาขา เทียบกับผู้ว่างงานแยกสาขาที่เรียน", "ข้อมูลตำแหน่งงานว่างของกรมการจัดหางานที่พบเป็นปี 2558–2559 และไม่ได้เชื่อมกับผู้ว่างงาน"],
            ["การเปลี่ยนแปลงโครงสร้างอุตสาหกรรม", "ผู้ว่างงานแยกอุตสาหกรรมเดิมต่อเนื่องหลายปี", "มีเพียงบางช่วง ยังไม่ได้นำมาตรวจสอบในโปรเจกต์นี้"],
            ["ความต้องการแรงงานลดลงในบางช่วง (Labour demand)", "ตำแหน่งงานว่างรายไตรมาสและอัตราการจ้างงานใหม่", "ข้อมูลกระทรวงแรงงานที่พบไม่ตอบสนองต่อการเรียกอัตโนมัติ จึงไม่ใช้"],
            ["ผู้ว่างงานแฝง/นอกกำลังแรงงาน (ไม่หางานแต่พร้อมทำงาน)", "ผู้ไม่อยู่ในกำลังแรงงานแยกเหตุผล", "ตารางกลุ่มอายุมีสถานภาพ 'ไม่หางานทำ/พร้อมทำงาน' ซึ่งนับรวมในผู้ว่างงานอยู่แล้ว ไม่ใช่ข้อมูลนอกกำลังแรงงาน"],
        ], columns=["สมมติฐาน", "หลักฐานที่ต้องมีเพื่อทดสอบ", "สถานะข้อมูลในโปรเจกต์"])
        st.dataframe(hyp, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# 6. Data sources and methodology
# ---------------------------------------------------------------------------


def methodology(ctx: Ctx) -> None:
    b = ctx.bundle
    ui.section_title("แหล่งข้อมูลและวิธีการ")
    pk = ctx.ckan.get("0706_02_0011", {})
    ui.notice("warn", "ชุดข้อมูล <code>0706_02_0011</code> ที่ระบุในโจทย์ตั้งต้นบน data.go.th คือ <b>"
                      + ui.esc(pk.get("title") or "อัตราการมีงานทำต่อประชากรวัยแรงงาน")
                      + "</b> (หน่วย: ร้อยละ) ไม่ใช่จำนวนผู้ว่างงาน จึงไม่นำมาแสดงเป็นจำนวนผู้ว่างงาน "
                        "ระบบใช้ชุดข้อมูลนี้ในหน้า ค่าจ้างและเศรษฐกิจ / กลุ่มประชากร / รายภูมิภาค (อัตรามีงานทำ) คู่กับ <code>0706_02_0019</code> ค่าจ้างเฉลี่ยของลูกจ้าง และใช้ชุดในตระกูลเดียวกัน (การสำรวจภาวะการทำงานของประชากร, สสช.) คือ <code>0706_02_0003</code> จำนวนผู้ว่างงาน และ <code>0706_02_0016</code> อัตราการว่างงาน "
                        '<a href="https://data.go.th/dataset/0706_02_0011" target="_blank" rel="noopener noreferrer">ดู ชุดข้อมูล ตั้งต้น ↗</a>', "ผลการตรวจสอบ ชุดข้อมูล หลัก")
    rows = []
    for s in config.SOURCES:
        stt = ctx.statuses.get(s.key, {})
        m = ctx.manifest.get(s.key, {})
        av = b.availability.get(s.key, {})
        rows.append({
            "ชุดข้อมูล": s.title, "หน่วยงาน": s.org, "หน่วย": s.unit, "ความถี่": s.frequency, "บทบาท": s.role,
            "ดึงข้อมูลเมื่อ": m.get("last_success_at", "—"),
            "สถานะไฟล์": {"fresh": "ล่าสุด", "stale": "เก่า", "cached_after_failure": "ใช้ แคช (ดึงใหม่ไม่สำเร็จ)", "missing": "ไม่มีไฟล์"}.get(stt.get("state"), "—"),
            "การตรวจสอบ": "ผ่าน" if av.get("ok") else ("ไม่ผ่าน/ไม่มี: " + (av.get("reason") or "")[:60]),
            "แถว": av.get("rows", 0), "ลิงก์ต้นทาง": m.get("url") or s.effective_url, "หน้าชุดข้อมูล": s.landing_url,
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, column_config={
        "ลิงก์ต้นทาง": st.column_config.LinkColumn("ลิงก์ต้นทาง"), "หน้าชุดข้อมูล": st.column_config.LinkColumn("หน้าชุดข้อมูล")})
    meta = [{"ชื่อ": v.get("title") or "—", "รหัส": k, "หน่วยงาน": v.get("organization") or "—", "ปีแรก": v.get("first_year_of_data") or "—",
             "ปีล่าสุด": v.get("last_year_of_data") or "—", "ข้อมูลปรับปรุงล่าสุด (ผู้เผยแพร่)": v.get("last_updated_date") or "—",
             "ข้อมูลกำกับ แก้ไขล่าสุด (data.go.th)": (v.get("metadata_modified") or "—")[:10]} for k, v in ctx.ckan.items() if "error" not in v]
    if meta:
        st.markdown("**ข้อมูลกำกับ จาก data.go.th (ระบบ API ของ data.go.th)**")
        st.dataframe(pd.DataFrame(meta), width="stretch", hide_index=True)

    nat = b.get("national")
    if len(nat):
        ui.section_title("ช่วงเวลาที่ครอบคลุม")
        st.write(f"จำนวนผู้ว่างงานรวม: {ui.period_range_text(nat)} · อัตราการว่างงาน: {ui.period_range_text(nat[nat['rate_pct'].notna()])} "
                 f"· GDP: {ui.period_range_text(b.get('gdp').dropna(subset=['gdp_yoy_pct'])) if b.has('gdp') else '—'}")
    ui.section_title("นิยามและสูตรคำนวณ")
    st.markdown("""
- **ผู้ว่างงาน (คน)** (สสช. เผยแพร่เป็นพันคน ระบบคูณ 1,000 ตอนแสดง): ผลรวมของตารางภาค × เขตการปกครอง (แบ่งประชากรแยกกัน ไม่ซ้ำซ้อน) ใช้เป็นยอดอ้างอิง และตรวจกับตารางการศึกษา/อายุ/เพศ/จังหวัด/ข้ามมิติ รายไตรมาส (เกณฑ์ ±1% หรือ ±0.15 พันคน)
- **อัตราการว่างงาน (%)** = ผู้ว่างงาน ÷ กำลังแรงงานรวม × 100 โดยใช้กำลังแรงงานรวมของ สสช. ชุดเดียวกัน (คน) และเทียบกับอัตราที่ สสช. เผยแพร่ (ยอมรับต่างได้ไม่เกิน 0.06 จุดตามการปัดเศษ) ไตรมาสที่ไม่ผ่านจะไม่แสดงอัตรา
- **อัตรารายเพศ** = ผู้ว่างงานเพศนั้น ÷ กำลังแรงงานเพศนั้น · **อัตรารายระดับการศึกษา** = ผู้ว่างงาน ÷ (ผู้ว่างงาน + ผู้มีงานทำ) ของระดับนั้น (ไม่รวมผู้รอฤดูกาล)
- **เทียบไตรมาสก่อน** = เทียบไตรมาสก่อนหน้า · **เทียบปีก่อน** = เทียบไตรมาสเดียวกันของปีก่อน ใช้เฉพาะเมื่อมีไตรมาสเปรียบเทียบจริง ไม่เป็นศูนย์เมื่อคำนวณไม่ได้
- **ช่วงเวลาที่เปลี่ยนแปลงผิดปกติ**: คะแนน z แบบทนทาน ของ เทียบปีก่อน% (มัธยฐาน/ส่วนเบี่ยงเบนสัมบูรณ์มัธยฐาน) |z| > 3
- **ปี**: ข้อมูล สสช. เป็น พ.ศ. (ตรวจจากค่าจริงก่อนใช้งาน) ข้อมูล สศช. เป็น ค.ศ. แปลงเป็น พ.ศ. ด้วย +543 หลังตรวจช่วงปีเท่านั้น
""")
    ui.section_title("วิธีจัดการข้อมูลที่หายไปและการเชื่อมข้อมูล")
    st.markdown("""
- ไม่เติม ไม่ประมาณ ไม่ ประมาณค่าช่วง ค่าที่ขาด: ไตรมาสที่ไม่มีข้อมูลหรือไม่ผ่านการตรวจสอบจะเป็นช่องว่างในกราฟ
- แถวซ้ำ ปีนอกช่วง ค่าติดลบ หน่วยผิด จะหยุดการนำตารางนั้นไปใช้ (ข้อผิดพลาด) และบันทึกใน `logs/`
- เชื่อม GDP กับการว่างงานด้วยคีย์ปี+ไตรมาสเท่านั้น หลังตรวจว่าทั้งสองชุดเป็นรายไตรมาสและคีย์ไม่ซ้ำ
- ข้อมูลดิบเก็บแยกใน `data/raw` ไม่ถูกแก้ไข; ตารางที่ทำความสะอาดแล้วอยู่ใน `data/processed`
""")
    ui.section_title("สถานะการตรวจสอบคุณภาพข้อมูล")
    rep = b.report.to_frame()
    n_err, n_warn = len(b.report.errors), len(b.report.warnings)
    (ui.notice("err", f"พบข้อผิดพลาด {n_err} รายการ ตารางที่เกี่ยวข้องถูกยกเว้น") if n_err
     else ui.notice("info", f"ไม่พบข้อผิดพลาดที่ทำให้ต้องยกเลิกตาราง · คำเตือน {n_warn} รายการ (ดูด้านล่าง)"))
    if len(rep):
        st.dataframe(rep.rename(columns={"severity": "ระดับ", "check": "การตรวจสอบ", "table": "ตาราง", "message": "รายละเอียด", "count": "จำนวน"}),
                     width="stretch", hide_index=True)
    ui.section_title("ข้อจำกัดในการตีความ")
    st.markdown("""
- ข้อมูลมาจากการสำรวจตัวอย่าง มีความคลาดเคลื่อนจากการสุ่ม โดยเฉพาะการแยกย่อยหลายมิติและระดับจังหวัด
- ข้อมูลรายไตรมาสไม่ปรับฤดูกาล เทียบไตรมาสก่อน จึงปนผลตามฤดูกาล
- ปี 2568 สสช. แยกเป็น 7 ภาค แดชบอร์ดรวมกลับเป็น 5 ภาค (ภาคกลาง+ตะวันออก, ภาคใต้+ใต้ชายแดน)
- ข้อมูลบางไตรมาสของตารางต้นฉบับไม่สอดคล้องกันเอง (ดูตารางตรวจสอบ) ระบบจึงยกเว้นแทนที่จะแก้เอง
- ไม่มีข้อมูลสาเหตุการว่างงานโดยตรงของประชากรทั้งประเทศ นอกจากเหตุผลที่ออกจากงานเดิม (ถึง ไตรมาส 4/2565) และข้อมูลผู้ประกันตน (ตัวแทน ปี 2563–2565)
""")
    ui.section_title("แหล่งข้อมูลที่ตรวจพบแต่ใช้ไม่ได้ / ตัวชี้วัด ที่คำนวณไม่ได้")
    st.markdown("""
- **กระทรวงแรงงาน** (`mol_66_04` ผู้ประกันตนขึ้นทะเบียนว่างงาน): การเชื่อมต่อถูกตัด  ขณะทดสอบ จึงไม่ใช้
- **กรมการจัดหางาน** ตำแหน่งงานว่างระดับประเทศบน data.go.th เป็นข้อมูลปี 2558–2559 (เก่าและไม่ต่อเนื่อง) จึงไม่นำมาใช้อธิบายความต้องการแรงงานปัจจุบัน
- **สำนักงานประกันสังคมรายจังหวัด** (`unem`) พบไฟล์ Excel ปี 2565–2568 แต่ยังไม่ได้ตรวจโครงสร้างจึงไม่ใช้
- **ธปท. / สศช.**: ธปท. ให้ข้อมูลเหตุผลที่ออกจากงาน (ถึง ไตรมาส 4/2565) · GDP ล่าสุดในไฟล์ที่เผยแพร่คือ ไตรมาส 4/2568
- **ตัวชี้วัด ที่คำนวณไม่ได้**: อัตราการว่างงานก่อนปี 2556, อัตรารายระดับการศึกษาเมื่อกรองภาค, อัตรารายเพศก่อน 2561, สาเหตุการว่างงานในปีหลัง 2565
""")
    ui.section_title("ลิงก์แหล่งข้อมูล")
    seen = set()
    for s in config.SOURCES:
        if s.landing_url not in seen:
            seen.add(s.landing_url)
            st.markdown(f"- [{s.org}: {s.landing_url}]({s.landing_url})")
