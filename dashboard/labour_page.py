"""Page 4: employment rate and average wage, read together with unemployment.

Everything here comes from tables that passed data_processing/labour_market.py. A quarter with no trustworthy value
is a gap (never interpolated). The window defaults to พ.ศ. 2563-2569 (config.JOINT_START_BE/END_BE), where all sources overlap and are checked.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import config
from analytics import metrics
from analytics import selectors as sel_
from dashboard import charts, theme
from dashboard import components as ui
from dashboard.pages import Ctx, _card_title, _ckey, _download, _period_pick, _plabel, _plabel_full, _plot, _src_url
from data_processing import labour_market as lm
from data_processing import normalize as nz

NATIONAL = lm.NATIONAL
SEX_COLORS = {"ชาย": theme.PRIMARY, "หญิง": theme.ACCENT}
SCOPE_FIXED = f"พ.ศ. {config.JOINT_START_BE}–{config.JOINT_END_BE} (ช่วงที่ทุกแหล่งซ้อนกัน)"
SCOPE_ALL = "ทุกไตรมาสที่มีข้อมูล"


def _pick(f, label: str, idxs: list[int], key: str, default: int | None = None) -> int | None:
    """Quarter picker limited to the quarters ticked in the sidebar (the window itself comes from the sidebar year)."""
    return _period_pick(label, sel_.quarter_ok(idxs, f), key, default)


def _scope_note(f, used: tuple, extra: str = "") -> None:
    """One line saying which sidebar filters this chart follows and which have no matching source table."""
    on = {"ภาค": bool(f.regions), "เพศ": f.sex_active, "การศึกษา": f.edu_active}
    ignored = [k for k, v in on.items() if v and k not in used]
    txt = "ตามตัวกรอง: ปี/ไตรมาส" + "".join(f" · {k}" for k in used if on.get(k))
    if ignored:
        txt += " · ไม่มีผล: " + ", ".join(ignored) + " (ไม่มีตารางต้นทางแยกมิตินี้)"
    st.caption(txt + extra)


def _national_frame(b, lo: int, hi: int, emp=None, wage=None, u=None) -> pd.DataFrame:
    """One row per quarter in [lo, hi]: unemployment rate (A), employment rate and wage (B); gaps stay NaN.

    ``emp`` / ``wage`` / ``u`` default to the national tables; the sidebar scope passes its own series."""
    base = b.get("lm_national")
    lmn = pd.DataFrame({
        "emp_pct": (emp if emp is not None else base).drop_duplicates("period_idx").set_index("period_idx")["emp_pct"],
        "wage": (wage if wage is not None else base).drop_duplicates("period_idx").set_index("period_idx")["wage"]})
    u = (u if u is not None else b.get("national")).drop_duplicates("period_idx").set_index("period_idx")
    fr = pd.DataFrame({"period_idx": range(lo, hi + 1)})
    fr["year_be"] = fr["period_idx"] // 4
    fr["quarter"] = fr["period_idx"] % 4 + 1
    fr["period_label"] = fr["period_idx"].map(lambda i: f"ไตรมาส {i % 4 + 1}/{i // 4}")
    fr["rate_pct"] = fr["period_idx"].map(u["rate_pct"])
    fr["u_k"] = fr["period_idx"].map(u["u_k"])
    fr["emp_pct"] = fr["period_idx"].map(lmn["emp_pct"])
    fr["wage"] = fr["period_idx"].map(lmn["wage"])
    return fr


def _scoped_frame(b, f, lo: int, hi: int):
    """(frame, scope label, notes): the three series for the region / sex picked in the sidebar (national when none)."""
    emp, wage, _hc, scope, notes = sel_.lm_scoped_series(b, f)
    u = sel_.unemployed_series(b, f).data
    if u is None or len(u) == 0:
        u = b.get("national")
    return _national_frame(b, lo, hi, emp, wage, u), scope, notes


def _latest(fr: pd.DataFrame, col: str):
    d = fr.dropna(subset=[col])
    return None if d.empty else d.iloc[-1]


def _yoy(fr: pd.DataFrame, col: str, idx: int):
    s = fr.set_index("period_idx")[col]
    cur, prev = s.get(idx, np.nan), s.get(idx - 4, np.nan)
    return None if pd.isna(cur) or pd.isna(prev) else (cur, prev)


def _gap_runs(idxs: list[int]) -> list[tuple[int, int]]:
    runs, start, prev = [], None, None
    for i in sorted(idxs):
        if start is None:
            start = prev = i
        elif i == prev + 1:
            prev = i
        else:
            runs.append((start, prev))
            start = prev = i
    if start is not None:
        runs.append((start, prev))
    return runs


def _trend_figure(fr: pd.DataFrame, lo: int, hi: int, wage_bad: list[int]) -> go.Figure:
    specs = [("rate_pct", "อัตราการว่างงาน (ร้อยละ)", theme.PRIMARY, "ร้อยละ", 2),
             ("emp_pct", "อัตราการมีงานทำ (ร้อยละของประชากรวัยทำงาน)", theme.MAGENTA, "ร้อยละ", 2),
             ("wage", "ค่าจ้างเฉลี่ยของลูกจ้าง (บาทต่อเดือน)", theme.SERIES[3], "บาท/เดือน", 0)]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.09, subplot_titles=[s[1] for s in specs])
    fig.update_annotations(font_size=13, xanchor="left", x=0)
    labels = fr["period_idx"].map(charts._label)
    for i, (col, title, color, unit, dec) in enumerate(specs, start=1):
        area = charts.area_under(fig, labels, fr[col], color, row=i, col=1)
        fig.add_trace(go.Scatter(
            x=labels, y=fr[col], mode="lines+markers", name=title, connectgaps=False, showlegend=False, **area,
            line=dict(color=color, width=2.4), marker=dict(size=5, color=color),
            hovertemplate="<b>%{x}</b><br>" + title.split(" (")[0] + ": %{y:,." + str(dec) + "f} " + unit + "<extra></extra>"), row=i, col=1)
    for a, z in _gap_runs([i for i in wage_bad if lo <= i <= hi]):
        fig.add_vrect(x0=charts._label(a), x1=charts._label(z), fillcolor=theme.BORDER, opacity=0.55, line_width=0, row=3, col=1,
                      annotation_text="ไม่มีค่าจ้างที่เชื่อถือได้", annotation_position="top left", annotation_font_size=11)
    charts.style(fig, height=640, top=44, legend_bottom=False)
    charts._category_x(fig, lo, hi, row=3, col=1)
    return fig


def _scatter_figure(d: pd.DataFrame, ycol: str, ytitle: str, yunit: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d["rate_pct"], y=d[ycol], mode="markers", name="รายไตรมาส", text=d["period_label"],
        marker=dict(size=10, color=d["year_be"], colorscale=[[0, "#FFD3E3"], [0.5, theme.PINK], [1, theme.PLUM]], showscale=True,
                    colorbar=dict(title=dict(text="ปี พ.ศ.", side="top"), orientation="h", thickness=10, len=0.7, x=0, xanchor="left",
                                  y=1.02, yanchor="bottom", tickfont=dict(size=11)), line=dict(color="white", width=1)),
        hovertemplate="<b>%{text}</b><br>อัตราการว่างงาน: %{x:.2f} ร้อยละ<br>" + ytitle + ": %{y:,.2f} " + yunit + "<extra></extra>"))
    fit = metrics.ols_line(d["rate_pct"], d[ycol])
    if fit:
        xs = np.array([d["rate_pct"].min(), d["rate_pct"].max()])
        fig.add_trace(go.Scatter(x=xs, y=fit[0] * xs + fit[1], mode="lines", name="เส้นแนวโน้มเชิงเส้น (กำลังสองน้อยที่สุด)",
                                 line=dict(color=theme.MAGENTA, width=2.4, dash="dash"), hoverinfo="skip"))
    charts.style(fig, height=430, ytitle=f"{ytitle} ({yunit})", top=78)
    fig.update_xaxes(title_text="อัตราการว่างงาน (ร้อยละ)")
    return fig


def _region_scatter(d: pd.DataFrame, ycol: str, ytitle: str, yunit: str, label_col: str | None = None) -> go.Figure:
    fig = go.Figure()
    for region, g in d.groupby("region", sort=False):
        fig.add_trace(go.Scatter(
            x=g["rate_pct"], y=g[ycol], mode="markers+text" if label_col else "markers", name=region,
            text=g[label_col] if label_col else None, textposition="top center", textfont=dict(size=11),
            marker=dict(size=12 if label_col else 8, color=charts.REGION_COLORS.get(region, theme.MIDBLUE), line=dict(color="white", width=1)),
            customdata=g["period_label"],
            hovertemplate="<b>" + str(region) + "</b> %{customdata}<br>อัตราการว่างงาน: %{x:.2f} ร้อยละ<br>" + ytitle + ": %{y:,.2f} " + yunit + "<extra></extra>"))
    charts.style(fig, height=430, ytitle=f"{ytitle} ({yunit})", top=24)
    fig.update_xaxes(title_text="อัตราการว่างงาน (ร้อยละ)")
    return fig


def _setup(ctx: Ctx, trend: bool = False):
    """(bundle, filters, lo, hi): the quarter window is the sidebar year (or every year); with ``trend`` it reaches back at
    least five years so trends and correlations have history even when one year is picked. None when the data is missing."""
    b, f = ctx.bundle, ctx.filters
    if not (b.has("lm_national") and b.has("national")):
        ui.empty_state("ยังไม่มีข้อมูลอัตรามีงานทำ/ค่าจ้างที่ผ่านการตรวจสอบ — กดรีเฟรชข้อมูล หรือดูสถานะในหน้า ที่มาและหลักฐาน")
        return None
    all_idx = pd.concat([b.get("lm_national")["period_idx"], b.get("national")["period_idx"]])
    lo = max(int(all_idx.min()), (f.for_trend() if trend else f).year_min * 4) if f.year_min else int(all_idx.min())
    hi = min(int(all_idx.max()), f.year_max * 4 + 3) if f.year_max else int(all_idx.max())
    if lo > hi:
        ui.empty_state("ไม่มีข้อมูลในปีที่เลือก ลองเลือกปีอื่นหรือ ทุกปี")
        return None
    return b, f, lo, hi


def national_section(ctx: Ctx) -> None:
    ui.section_title("ค่าจ้างและการมีงานทำ เมื่ออ่านร่วมกับการว่างงาน")
    st_ = _setup(ctx, trend=True)
    if st_ is None:
        return
    b, f, lo, hi = st_
    ui.notice("info", "ส่วนนี้เพิ่ม <b>อัตราการมีงานทำ</b> และ <b>ค่าจ้างเฉลี่ยของลูกจ้าง</b> ของ สสช. เข้ามาอ่านคู่กับอัตราการว่างงาน "
                      "ทั้งสามเป็นรายไตรมาส จับคู่ด้วยปี+ไตรมาส · อัตรามีงานทำคิดจากประชากรวัยทำงานทั้งหมด ส่วนอัตราการว่างงานคิดจากกำลังแรงงาน "
                      "จึงไม่ใช่ค่าตรงข้ามกัน · ค่าจ้างเป็นราคาปัจจุบัน (ไม่ปรับเงินเฟ้อ) เฉพาะลูกจ้าง", "อ่านก่อน: ตัวชี้วัดเหล่านี้ต่างกันอย่างไร")
    fr, scope, scope_notes = _scoped_frame(b, f, lo, hi)
    is_nat = scope == "ทั่วประเทศ"
    wage_bad = [int(i) for i in b.excluded.get("lm_wage", [])] if is_nat else []
    emp_bad = [int(i) for i in b.excluded.get("lm_emp", [])] if is_nat else []
    _scope_note(f, ("ภาค", "เพศ"), f" · ขอบเขตอัตรามีงานทำและค่าจ้าง: {scope}")
    for n in scope_notes:
        st.caption(":material/info: " + n)

    e, w, u = _latest(fr, "emp_pct"), _latest(fr, "wage"), _latest(fr, "rate_pct")
    both = fr.dropna(subset=["rate_pct", "emp_pct", "wage"])
    n_win = len(fr)

    # ---- key finding: only sentences made of the numbers on this page -----------------------------------
    if e is not None and w is not None:
        u_at_e = fr.loc[fr["period_idx"] == e["period_idx"], "rate_pct"].iloc[0]
        txt = (f"มีงานทำ <b>{ui.fmt_num(e['emp_pct'], 2)}%</b> ({ui.esc(_plabel(int(e['period_idx'])))}) · "
               f"ค่าจ้าง <b>฿{ui.fmt_num(w['wage'], 0)}</b> ({ui.esc(_plabel(int(w['period_idx'])))})")
        if not pd.isna(u_at_e):
            txt += f" · ว่างงาน <b>{ui.fmt_num(u_at_e, 2)}%</b> (ไตรมาสเดียวกับมีงานทำ)"
        ui.callout("สรุป", txt)
    st.write("")

    # ---- KPI cards -------------------------------------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)

    def delta_pp(col, row, dec=2):
        y = _yoy(fr, col, int(row["period_idx"]))
        return "เทียบปีก่อน: ไม่มีข้อมูล" if y is None else f"เทียบปีก่อน: {ui.fmt_signed(y[0] - y[1], dec, ' จุด')}"

    if e is not None:
        k1.markdown(ui.kpi_card("อัตราการมีงานทำ", ui.fmt_num(e["emp_pct"], 2), "%", delta_pp("emp_pct", e), None,
                                "สสช. OS_02_0016_03 · " + _plabel_full(int(e["period_idx"]))), unsafe_allow_html=True)
    if w is not None:
        y = _yoy(fr, "wage", int(w["period_idx"]))
        sub = "เทียบปีก่อน: ไม่มีข้อมูล" if y is None else f"เทียบปีก่อน: {ui.fmt_signed((y[0] / y[1] - 1) * 100, 1, '%')}"
        k2.markdown(ui.kpi_card("ค่าจ้างเฉลี่ยของลูกจ้าง", ui.fmt_num(w["wage"], 0), "บาท/เดือน", sub, None,
                                "สสช. OS_02_0024_01 · " + _plabel_full(int(w["period_idx"]))), unsafe_allow_html=True)
    if u is not None:
        k3.markdown(ui.kpi_card("อัตราการว่างงาน", ui.fmt_num(u["rate_pct"], 2), "%", delta_pp("rate_pct", u), "rate",
                                "สสช. (คำนวณจากผู้ว่างงาน ÷ กำลังแรงงาน) · " + _plabel_full(int(u["period_idx"]))), unsafe_allow_html=True)
    k4.markdown(ui.kpi_card("ไตรมาสที่มีครบทั้งสามค่า", f"{len(both)}/{n_win}", "ไตรมาส", f"ค่าจ้างไม่แสดง {len(wage_bad)} ไตรมาส" if wage_bad else "", None,
                            "ผลการตรวจข้ามตารางโดยอัตโนมัติ"), unsafe_allow_html=True)
    if wage_bad:
        ui.notice("warn", "สสช. เผยแพร่ค่าจ้างเฉลี่ยระดับประเทศของไตรมาส " + ui.esc(", ".join(_plabel(i) for i in sorted(wage_bad))) +
                  " จาก 3 ตารางที่ <b>ขัดแย้งกันเอง</b> (หรือเด้งผิดปกติจากไตรมาสข้างเคียงเกิน 10%) และไม่มีเหตุผลทางข้อมูลที่จะเลือกตารางใดเป็นฝ่ายถูก "
                  "ระบบจึงเว้นค่าจ้างของไตรมาสเหล่านี้ <b>ในทุกกราฟ</b> เป็นช่องว่าง ไม่ประมาณค่าแทน", "ค่าจ้างบางไตรมาสไม่แสดง",
                  brief=f" {len(wage_bad)} ไตรมาส ({_plabel(min(wage_bad))} – {_plabel(max(wage_bad))}) เพราะตารางต้นทางขัดแย้งกัน")
    if emp_bad:
        ui.notice("info", "อัตรามีงานทำของ " + ui.esc(", ".join(_plabel(i) for i in sorted(emp_bad))) + " ตารางต้นทางให้ค่าต่างกัน จึงเว้นไว้", "อัตรามีงานทำบางไตรมาสไม่แสดง")

    # ---- 1) national trend -----------------------------------------------------------------------------
    ui.section_title("แนวโน้มรายไตรมาส: ว่างงาน มีงานทำ และค่าจ้าง")
    _plot(_trend_figure(fr, lo, hi, wage_bad), "lm_trend")
    ui.chart_caption("สสช. (ผู้ว่างงานและกำลังแรงงาน OS_02_0003_01 / OS_02_0001_01; อัตรามีงานทำ OS_02_0016_03; ค่าจ้าง OS_02_0024_01)",
                     ui.period_range_text(fr.dropna(subset=["rate_pct", "emp_pct", "wage"], how="all")), "ร้อยละ / ร้อยละ / บาทต่อเดือน",
                     "ระดับประเทศ ทุกเพศ ทุกอายุ ทุกการศึกษา ใช้แถวรวมของต้นทาง ไม่ใช่ค่าเฉลี่ยของกลุ่มย่อย",
                     "ข้อมูลไม่ปรับฤดูกาล · ช่องว่างคือไตรมาสที่ไม่มีค่าที่เชื่อถือได้ ไม่ใช่ค่าศูนย์ · อัตรามีงานทำสิ้นสุดก่อนอัตราการว่างงาน/ค่าจ้างล่าสุด",
                     _src_url("nso_er_sex_age"))
    _download(fr[["period_label", "rate_pct", "emp_pct", "wage"]].rename(columns={"emp_pct": "emp_rate_pct", "wage": "wage_baht"}),
              "unemployment_employment_wage_national", "dl_lm_nat")

    # ---- 2) relationship over time ------------------------------------------------------------------------
    ui.section_title("ความสัมพันธ์ระหว่างการว่างงานกับการมีงานทำ/ค่าจ้าง (รายไตรมาส)", "corr")
    c1, c2 = st.columns(2)
    ymode = c1.radio("เทียบอัตราการว่างงานกับ", ["อัตราการมีงานทำ (%)", "ค่าจ้างเฉลี่ย (บาท/เดือน)"], horizontal=True, key="lm_y")
    drop_covid = c2.checkbox("ตัดไตรมาสปี 2563–2564 ออก (ทดสอบความไวของผล)", value=False, key="lm_covid")
    ycol, ytitle, yunit = ("emp_pct", "อัตราการมีงานทำ", "ร้อยละ") if ymode.startswith("อัตรา") else ("wage", "ค่าจ้างเฉลี่ย", "บาท/เดือน")
    d = fr.dropna(subset=["rate_pct", ycol])
    if drop_covid:
        d = d[~d["year_be"].isin([2563, 2564])]
    cs = metrics.correlation_summary(d["rate_pct"], d[ycol])
    if cs["reason"]:
        ui.empty_state(cs["reason"])
    else:
        _plot(_scatter_figure(d, ycol, ytitle, yunit), "lm_sc")
        m1, m2, m3 = st.columns(3)
        m1.metric("สหสัมพันธ์เพียร์สัน (r)", f"{cs['pearson']:.2f}", help=f"ช่วงความเชื่อมั่น 95% โดยประมาณ: {cs['ci_low']:.2f} ถึง {cs['ci_high']:.2f}")
        m2.metric("สหสัมพันธ์สเปียร์แมน (ρ)", f"{cs['spearman']:.2f}", help="สหสัมพันธ์เชิงอันดับ ทนต่อค่าสุดโต่งมากกว่าเพียร์สัน")
        m3.metric("จำนวนไตรมาสที่ใช้ (n)", f"{cs['n']}")
        if abs(cs["pearson"] - cs["spearman"]) > 0.25:
            ui.notice("warn", "สหสัมพันธ์เพียร์สันกับสเปียร์แมนต่างกันมาก ผลถูกกำหนดโดยไม่กี่จุดสุดโต่ง ควรตีความด้วยความระมัดระวัง")
    if ycol == "wage":
        ui.notice("warn", "ค่าจ้างเป็นราคาปัจจุบันและมีแนวโน้มเพิ่มตามเวลา ส่วนอัตราการว่างงานผันผวนตามช่วงโควิด สหสัมพันธ์จึงอาจสะท้อนเพียง <b>ช่วงเวลาที่เหมือนกัน</b> "
                          "ไม่ใช่ความเกี่ยวข้องโดยตรง ลองตัดปี 2563–2564 เพื่อดูว่าผลเปลี่ยนหรือไม่", "ข้อควรระวังเรื่องค่าจ้าง",
                  brief=" ค่าจ้างเพิ่มตามเวลา ผลอาจเป็นแค่ช่วงเวลาร่วมกัน ลองตัดปีโควิด")
    ui.notice("info", "ค่าสหสัมพันธ์บอกเพียงว่าตัวเลขสองชุดเคลื่อนไหวสัมพันธ์กันหรือไม่ <b>ไม่ได้พิสูจน์ว่าชุดหนึ่งเป็นสาเหตุของอีกชุด</b> "
                      "ใช้เฉพาะไตรมาสที่มีทั้งสองค่าที่ผ่านการตรวจสอบ", "สหสัมพันธ์ไม่ใช่ความเป็นเหตุเป็นผล")

    ui.section_title("คุณภาพข้อมูลของหน้านี้")
    rep = b.report.to_frame()
    mine = rep[rep["table"].isin(["nso_er_sex_age", "nso_er_edu", "nso_er_region_sex", "nso_w_age", "nso_w_edu", "nso_w_industry",
                                  "employment_rate", "avg_wage", "labour_market"])]
    if len(mine):
        with st.expander(f"รายการตรวจสอบอัตรามีงานทำ/ค่าจ้าง ({len(mine)} รายการ)"):
            st.dataframe(mine.rename(columns={"severity": "ระดับ", "check": "การตรวจสอบ", "table": "ตาราง", "message": "รายละเอียด", "count": "จำนวน"}),
                         width="stretch", hide_index=True)
    ui.notice("info", "เกณฑ์: ค่าจ้างเฉลี่ยประเทศจาก 3 ตารางต้องต่างกันไม่เกิน 1% และไม่เด้งจากไตรมาสข้างเคียงเกิน 10% · อัตรามีงานทำจาก 3 ตารางต้องต่างกันไม่เกิน "
                      "0.05 จุด · ค่าจ้าง 0 บาท หรืออัตรา 0%/100% พอดี (กลุ่มตัวอย่างเล็ก) ถือว่าไม่มีข้อมูล · คีย์ซ้ำที่ค่าขัดแย้งกันไม่ถูกใช้", "วิธีตรวจสอบ")


def region_section(ctx: Ctx) -> None:
    st_ = _setup(ctx)
    if st_ is None:
        return
    b, f, lo, hi = st_
    # ---- 3) regions ------------------------------------------------------------------------------------------
    ui.section_title("เปรียบเทียบรายภูมิภาค")
    rs = b.get("region_series")
    if not {"emp_pct", "wage"}.issubset(rs.columns):
        ui.empty_state("ไม่มีข้อมูลรายภาคของอัตรามีงานทำ/ค่าจ้างที่ผ่านการตรวจสอบ")
    else:
        rs = rs[rs["period_idx"].between(lo, hi)]
        picked = [r for r in f.regions if r in set(rs["region"])]
        have = sorted(int(i) for i in rs.dropna(subset=["rate_pct"]).loc[rs["emp_pct"].notna() | rs["wage"].notna(), "period_idx"].unique())
        ridx = _pick(f, "ไตรมาส (รายภาค)", have, "lm_reg_period")
        _scope_note(f, ("ภาค",), " · แผนที่และกราฟแสดงเฉพาะภาคที่เลือก" if picked else "")
        if ridx is not None:
            cur = rs[rs["period_idx"] == ridx].copy()
            if picked:
                cur = cur[cur["region"].isin(picked)]
            cur["period_label"] = _plabel(ridx)
            with st.container(border=True, key=_ckey()):
                _card_title("ว่างงาน × ค่าจ้าง รายภาค", f"{_plabel(ridx)} · หนึ่งจุดคือหนึ่งภูมิภาค")
                pts = cur.dropna(subset=["rate_pct", "wage"])
                if len(pts) < 3 and picked:
                    ui.empty_state("เลือกภูมิภาคไม่ถึง 3 ภาค จึงไม่วาดกราฟกระจายของภาค (ดูแนวโน้มของภาคที่เลือกด้านล่าง) ล้างตัวกรองภาคเพื่อเทียบทั้ง 5 ภาค")
                elif len(pts) < 3:
                    ui.empty_state("ไตรมาสนี้มีภูมิภาคที่มีทั้งอัตราการว่างงานและค่าจ้างน้อยกว่า 3 ภาค (ค่าจ้างของไตรมาสนี้อาจถูกเว้น) จึงไม่วาดกราฟ")
                else:
                    pts = pts.assign(short=pts["region"].str.replace("ภาค", "", regex=False))
                    st.plotly_chart(_region_scatter(pts, "wage", "ค่าจ้างเฉลี่ย", "บาท/เดือน", "short"), width="stretch", key="lm_reg_sc",
                                    config={"displayModeBar": False})
                    missing = [r for r in ("กรุงเทพมหานคร", "ภาคเหนือ", "ภาคตะวันออกเฉียงเหนือ", "ภาคกลาง", "ภาคใต้") if r not in set(pts["region"])]
                    note = f"มี {len(pts)} จุด จึงไม่คำนวณสหสัมพันธ์"
                    if missing and not picked:
                        note += " · ไม่มีจุดของ " + ", ".join(missing) + " เพราะไตรมาสนี้ไม่มีค่าจ้างที่เชื่อถือได้ของภาคนั้น (ตั้งแต่ปี 2568 สสช. แยกภาคกลางและภาคใต้เป็นภาคย่อย รวมค่าจ้างกลับไม่ได้) ระบบไม่ประมาณค่าแทน"
                    st.caption(note)
            tbl = cur[["region", "rate_pct", "emp_pct", "wage"]].rename(columns={
                "region": "ภูมิภาค", "rate_pct": "อัตราการว่างงาน (%)", "emp_pct": "อัตรามีงานทำ (%)", "wage": "ค่าจ้างเฉลี่ย (บาท/เดือน)"})
            st.dataframe(tbl, width="stretch", hide_index=True, column_config={
                "อัตราการว่างงาน (%)": st.column_config.NumberColumn(format="%.2f"), "อัตรามีงานทำ (%)": st.column_config.NumberColumn(format="%.2f"),
                "ค่าจ้างเฉลี่ย (บาท/เดือน)": st.column_config.NumberColumn(format="%.0f")})
            ui.chart_caption("สสช. (ผู้ว่างงาน/กำลังแรงงานรายภาค, อัตรามีงานทำ OS_02_0016_03, ค่าจ้าง OS_02_0024_01)", _plabel_full(ridx), "ร้อยละ / บาทต่อเดือน",
                             "ค่าแต่ละภาคตามที่ สสช. เผยแพร่ (ผ่านการตรวจยอดรวมกับตารางอ้างอิงอีกตาราง)",
                             "ตั้งแต่ปี 2568 สสช. แยกภาคตะวันออกและใต้ชายแดน แดชบอร์ดรวมกลับเป็น 5 ภาค: อัตรามีงานทำและค่าจ้างของภาคกลาง/ใต้รวมไม่ได้จึงเป็นช่องว่าง · ช่องว่างคือไม่มีค่าที่ผ่านการตรวจ",
                             _src_url("nso_w_age"))
            # pooled region x quarter scatter
            pool = rs.dropna(subset=["rate_pct", "wage"]).copy()
            pool["period_label"] = pool["period_idx"].map(_plabel)
            if picked:
                tr = rs[rs["region"].isin(picked)].copy()
                tr["period_label"] = tr["period_idx"].map(_plabel)
                st.markdown("**แนวโน้มของภาคที่เลือก**")
                t1, t2 = st.columns(2)
                for box, col_, ttl_, unit_, dec_ in ((t1, "emp_pct", "อัตรามีงานทำ", "ร้อยละ", 2), (t2, "wage", "ค่าจ้างเฉลี่ย", "บาท/เดือน", 0)):
                    with box:
                        if tr[col_].notna().sum() >= 2:
                            cf_ = (b.availability.get("conflicts") or {}).get("emp" if col_ == "emp_pct" else "wage", [])
                            lo_c, hi_c = int(tr["period_idx"].min()), int(tr["period_idx"].max())
                            _plot(charts.multi_line(tr, col_, "region", ttl_, unit_, dec_, excluded=[r["period_idx"] for r in cf_ if lo_c <= r["period_idx"] <= hi_c]), f"lm_regtr_{col_}")
                            ui.conflict_box(cf_, _plabel, lo_c, hi_c, f" ของ{ttl_}")
                        else:
                            ui.empty_state(f"{ttl_}: มีค่าไม่ถึง 2 ไตรมาสในปีที่เลือก (ลองเลือก ทุกปี)")
            elif len(pool) >= 12:
                st.markdown("**ทุกภาคทุกไตรมาสในช่วงที่เลือก**")
                _plot(_region_scatter(pool, "wage", "ค่าจ้างเฉลี่ย", "บาท/เดือน"), "lm_pool")
                cs2 = metrics.correlation_summary(pool["rate_pct"], pool["wage"])
                ui.chart_caption("สสช. (เช่นเดียวกับด้านบน)", ui.period_range_text(pool), "ร้อยละ / บาทต่อเดือน",
                                 f"จุดละหนึ่งภาค×ไตรมาส (n = {len(pool)}" + ("" if cs2["reason"] else f", r = {cs2['pearson']:.2f}") + ")",
                                 "จุดจากภาคเดียวกันต่างไตรมาสไม่เป็นอิสระต่อกัน และค่าจ้างเพิ่มตามเวลา จึงไม่ควรตีความ r เป็นความสัมพันธ์เชิงเหตุผล", _src_url("nso_w_age"))


def _one(values, default):
    """The single value ticked in the sidebar, else ``default`` (the national / all-sexes row)."""
    return values[0] if len(values) == 1 else default


def _groups(b, f, lo: int, hi: int, which: str) -> None:
    edu = b.get("lm_edu")
    resid = set(lm.RESIDUAL_EDU) | {"รวม"}

    tabs_labels = ["การศึกษา", "จำนวนผู้มีงานทำ"]

    if which == tabs_labels[0]:
        if edu.empty:
            ui.empty_state("ไม่มีข้อมูลรายการศึกษาที่ผ่านการตรวจสอบ")
            return
        reg, sx = _one(list(f.regions), NATIONAL), _one(list(f.sexes), "รวม")
        d = edu[(edu["region"] == reg) & (edu["area"] == "รวม") & (edu["sex"] == sx) & ~edu["edu"].isin(resid)]
        d = d[d["period_idx"].between(lo, hi)]
        extra = " · ภาคมากกว่าหนึ่งภาคแสดงระดับประเทศ" if len(f.regions) > 1 else ""
        _scope_note(f, ("ภาค", "เพศ", "การศึกษา"), extra)
        full = d.groupby("period_idx").agg(e=("emp_pct", "count"), w=("wage", "count"))
        idxs = [int(i) for i in full.index[(full["e"] >= 6) | (full["w"] >= 6)]]
        idx = _pick(f, "ไตรมาส", idxs, "lm_edu_period", default=max([i for i in sel_.quarter_ok(idxs, f) if full.loc[i, "e"] >= 6 and full.loc[i, "w"] >= 6], default=None))
        if idx is None:
            ui.empty_state("ไม่มีไตรมาสที่มีข้อมูลการศึกษาครบพอในช่วงที่เลือก")
            return
        cur = d[d["period_idx"] == idx]
        if f.edu_active:
            cur = cur[cur["edu"].map(nz.normalize_education_group).isin(f.edus)]
        order = [x for x in ["ไม่มีการศึกษา", "ต่ำกว่าประถมศึกษา", "ประถมศึกษา", "มัธยมศึกษาตอนต้น", "มัธยมศึกษาตอนปลาย สายสามัญ",
                              "มัธยมศึกษาตอนปลาย สายอาชีวศึกษา", "มัธยมศึกษาตอนปลาย สายวิชาการศึกษา", "อุดมศึกษา สายวิชาชีพ", "อุดมศึกษา สายวิชาการ",
                              "อุดมศึกษา สายวิชาการศึกษา"] if x in set(cur["edu"])]
        cur = cur.set_index("edu").reindex(order).reset_index()
        fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04, subplot_titles=("อัตราการมีงานทำ (ร้อยละ)", "ค่าจ้างเฉลี่ย (บาทต่อเดือน)"))
        # each title starts at the left edge of ITS OWN panel (x=0 for both made them print on top of each other)
        for ann, axis in zip(fig.layout.annotations, (fig.layout.xaxis, fig.layout.xaxis2)):
            ann.update(x=axis.domain[0], xanchor="left", font=dict(size=13))
        ylab = [charts._wrap(x) for x in cur["edu"]]
        fig.add_trace(go.Bar(y=ylab, x=cur["emp_pct"], orientation="h", marker_color=theme.MAGENTA, name="อัตราการมีงานทำ", showlegend=False,
                             text=[f"{v:.1f}" if v == v else "" for v in cur["emp_pct"]], textposition="outside", cliponaxis=False,
                             hovertemplate="<b>%{customdata}</b><br>อัตราการมีงานทำ: %{x:.1f} ร้อยละ<extra></extra>", customdata=cur["edu"]), row=1, col=1)
        fig.add_trace(go.Bar(y=ylab, x=cur["wage"], orientation="h", marker_color=theme.PRIMARY, name="ค่าจ้างเฉลี่ย", showlegend=False,
                             text=[f"{v:,.0f}" if v == v else "" for v in cur["wage"]], textposition="outside", cliponaxis=False,
                             hovertemplate="<b>%{customdata}</b><br>ค่าจ้างเฉลี่ย: ฿%{x:,.0f} ต่อเดือน<extra></extra>", customdata=cur["edu"]), row=1, col=2)
        charts.style(fig, height=max(360, 62 * len(cur) + 90), legend_bottom=False, top=40)
        fig.update_yaxes(autorange="reversed", gridcolor="white")
        charts._pad_range(fig, cur["emp_pct"].dropna().tolist() or [1])
        fig.update_xaxes(range=[0, max(cur["wage"].dropna().max() * 1.28, 1)] if cur["wage"].notna().any() else None, row=1, col=2)
        fig.update_xaxes(range=[0, 118], row=1, col=1)
        no_wage = not cur["wage"].notna().any()
        if no_wage:   # say so inside the empty panel instead of leaving a blank axis
            fig.update_xaxes(range=[0, 1], showticklabels=False, showgrid=False, title_text="", row=1, col=2)
            fig.add_annotation(xref="x2 domain", yref="paper", x=0.5, y=0.5, showarrow=False, align="center",
                               text="ไม่มีค่าจ้างรายการศึกษา<br>ที่ผ่านการตรวจสอบในไตรมาสนี้", font=dict(size=13, color=theme.MUTED))
        _plot(fig, "lm_edu_fig")
        if no_wage:
            w_ok = [int(i) for i in full.index[full["w"] >= 6]]
            st.caption(":material/info: ไตรมาสนี้มีเฉพาะอัตรามีงานทำ ค่าจ้างของไตรมาสที่ตารางต้นทางขัดแย้งกันถูกเว้นไว้ ไม่ประมาณค่าแทน"
                       + (f" · ค่าจ้างล่าสุดในช่วงที่เลือก: {_plabel(max(w_ok))} (เลือกได้ที่ตัวเลือกไตรมาสด้านบน)" if w_ok else
                          " · ลองเลือกปีอื่นหรือ ทุกปี ที่ตัวกรอง"))
        miss = [x for x, e_, w_ in zip(cur["edu"], cur["emp_pct"], cur["wage"]) if pd.isna(e_) or pd.isna(w_)]
        ui.chart_caption("สสช. OS_02_0016_02 (อัตรามีงานทำ) และ OS_02_0024_02 (ค่าจ้าง)", _plabel_full(idx), "ร้อยละ / บาทต่อเดือน",
                         "แถวของแต่ละระดับการศึกษาตามที่ สสช. เผยแพร่ (ระดับประเทศ ทุกเพศ ทุกเขต)",
                         "กลุ่มที่ไม่มีค่าที่เชื่อถือได้ (ค่าจ้าง 0 บาท หรืออัตรา 0%/100% พอดีจากกลุ่มตัวอย่างเล็ก) เป็นช่องว่าง"
                         + (f" · ช่องว่างไตรมาสนี้: {', '.join(miss)}" if miss else "") + " · ไม่รวมหมวด อื่น ๆ / ไม่ทราบ",
                         _src_url("nso_er_edu"))
        _download(cur.rename(columns={"edu": "education", "emp_pct": "emp_rate_pct", "wage": "wage_baht"}), "employment_wage_by_education", "dl_lm_edu")

    elif which == tabs_labels[1]:
        _employed_persons(b, f, lo, hi)


def _employed_persons(b, f, lo: int, hi: int) -> None:
    """Employed persons (shown in persons; the table is in thousands) from NSO OS_02_0002_01, checked against NSO LFS_02_20535_1."""
    nat = b.get("lm_employed_national")
    hc = b.get("lm_headcount")
    if nat.empty or hc.empty:
        ui.empty_state("ไม่มีข้อมูลจำนวนผู้มีงานทำที่ผ่านการตรวจสอบ (ตาราง สสช. OS_02_0002_01)")
        return
    _scope_note(f, ("ภาค", "เพศ"))
    regs, sxs = list(f.regions), list(f.sexes)
    if regs or sxs:
        g = sel_._headcount_series(hc, regs, sxs)[["period_idx", "emp_k"]]
        nat = g.merge(nat[["period_idx", "checked_vs_nso"]], on="period_idx", how="left")
        nat["checked_vs_nso"] = nat["checked_vs_nso"].fillna(False).astype(bool)
        hc = hc[(hc["region"].isin(regs) if regs else True) & (hc["sex"].isin(sxs) if sxs else True)]
    d = nat[nat["period_idx"].between(lo, hi)]
    if d.empty:
        ui.empty_state("ไม่มีข้อมูลจำนวนผู้มีงานทำในช่วงเวลาที่เลือก")
        return
    full = pd.DataFrame({"period_idx": range(int(d["period_idx"].min()), int(d["period_idx"].max()) + 1)}).merge(d, on="period_idx", how="left")
    full["x"] = full["period_idx"].map(charts._label)
    full["emp_k"] = full["emp_k"] * 1000.0
    fig = go.Figure()
    area = charts.area_under(fig, full["x"], full["emp_k"], theme.PRIMARY)
    fig.add_trace(go.Scatter(x=full["x"], y=full["emp_k"], mode="lines+markers", name="ผู้มีงานทำ", connectgaps=False, **area,
                             line=dict(color=theme.PRIMARY, width=2.4), marker=dict(size=5, color=theme.PRIMARY),
                             hovertemplate="<b>%{x}</b><br>ผู้มีงานทำ: %{y:,.0f} คน<extra></extra>"))
    charts.style(fig, ytitle="ผู้มีงานทำ (คน)", height=380, top=24, legend_bottom=False)
    charts._category_x(fig, int(full["period_idx"].min()), int(full["period_idx"].max()))
    _plot(fig, "lm_emp_total")
    ui.chart_caption("สสช. OS_02_0002_01 จำนวนผู้มีงานทำ ตรวจกับ สสช. LFS_02_20535_1", ui.period_range_text(d.assign(period_label=d["period_idx"].map(_plabel))), "คน",
                     "ผลรวมทุกภาค ทุกเพศ ทุกกลุ่มอายุ (ภาคแบ่งประเทศโดยไม่ซ้ำซ้อน) เฉพาะไตรมาสที่ครบทุกภาค×เพศ×อายุ",
                     "ไม่ได้ปรับฤดูกาล · ไตรมาสที่ไม่ผ่านการตรวจกับ สสช. หรือข้อมูลไม่ครบเป็นช่องว่าง · ผู้มีงานทำ + ผู้ว่างงาน ใกล้เคียงกำลังแรงงานรวม (ส่วนต่างคือผู้รอฤดูกาล)",
                     _src_url("nso_emp_region_sex"))

    idxs = sorted(int(i) for i in d["period_idx"].unique())
    idx = _pick(f, "ไตรมาส (โครงสร้างผู้มีงานทำ)", idxs, "lm_hc_period")
    if idx is None:
        return
    cur = hc[(hc["period_idx"] == idx) & (hc["area"] == "รวม")]
    by = cur.groupby(["sex", "age_group"], as_index=False)["emp_k"].sum()
    by["age_group"] = pd.Categorical(by["age_group"], ["15-19 ปี", "20-24 ปี", "25-29 ปี", "30-34 ปี", "35-39 ปี", "40-49 ปี", "50-59 ปี", "60 ปีขึ้นไป"], ordered=True)
    by = by.sort_values("age_group")
    _plot(charts.grouped_bar(by.assign(emp_k=by["emp_k"] * 1000.0), "age_group", "emp_k", "sex", "ผู้มีงานทำ", "คน", 0), "lm_hc_age")
    tot = by["emp_k"].sum()
    if tot > 0:
        st.caption(f"{_plabel_full(idx)} · รวม {tot * 1000:,.0f} คน · ชาย {by[by['sex'] == 'ชาย']['emp_k'].sum() / tot * 100:.1f}% หญิง {by[by['sex'] == 'หญิง']['emp_k'].sum() / tot * 100:.1f}%")
    ui.chart_caption("สสช. OS_02_0002_01 จำนวนผู้มีงานทำ ตรวจกับ สสช. LFS_02_20535_1 ที่ระดับภาค×เพศ", _plabel_full(idx), "คน",
                     "ผลรวมของทุกภาคในไตรมาสนั้นแยกตามเพศและกลุ่มอายุ", "ตัวเลขกลุ่มอายุ×เพศไม่มีตารางอ้างอิงของ สสช. ให้ตรวจโดยตรง (ตรวจได้ที่ผลรวมของภาค×เพศเท่านั้น)",
                     _src_url("nso_emp_region_sex"))
    _download(by.assign(age_group=by["age_group"].astype(str)), "employed_persons_by_sex_age", "dl_lm_hc")


def group_section(ctx: Ctx, which: str) -> None:
    """which: one of GROUPS."""
    st_ = _setup(ctx)
    if st_ is None:
        return
    b, f, lo, hi = st_
    _groups(b, f, lo, hi, which)


GROUPS = ["การศึกษา", "จำนวนผู้มีงานทำ"]
