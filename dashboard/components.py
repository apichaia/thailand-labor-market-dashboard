"""Reusable UI pieces: ตัวชี้วัด cards, notices, glossary tooltips, chart captions."""
from __future__ import annotations

import html
import math

import pandas as pd
import streamlit as st

GLOSSARY = {
    "unemployed": "จำนวนผู้ว่างงาน: ผู้อายุ 15 ปีขึ้นไปที่ไม่มีงานทำ พร้อมทำงาน และหางานทำ (หรือพร้อมทำงาน) ตามนิยามการสำรวจภาวะการทำงานของประชากรขององค์การแรงงานระหว่างประเทศ แสดงเป็นจำนวนคน (ต้นทางเผยแพร่เป็นพันคน)",
    "rate": "อัตราการว่างงาน = ผู้ว่างงาน ÷ กำลังแรงงานรวม × 100 ใช้จำนวนผู้ว่างงานและกำลังแรงงานชุดเดียวกัน ช่วงเวลาและขอบเขตเดียวกัน",
    "labor_force": "กำลังแรงงานรวม: ผู้มีงานทำ + ผู้ว่างงาน + ผู้รอฤดูกาล (อายุ 15 ปีขึ้นไป) ใช้เป็นตัวหารของอัตราการว่างงาน",
    "yoy": "การเปลี่ยนแปลงเทียบปีก่อน: เทียบกับไตรมาสเดียวกันของปีก่อน (ลดผลของฤดูกาล) ต่างจากการเทียบไตรมาสก่อนหน้า ซึ่งข้อมูลนี้ไม่ได้ปรับฤดูกาล จึงไม่ควรเทียบสองตัวชี้วัดนี้ว่าเป็นอย่างเดียวกัน",
    "qoq": "การเปลี่ยนแปลงเทียบไตรมาสก่อน: เทียบกับไตรมาสก่อนหน้า ข้อมูลไม่ได้ปรับฤดูกาล การเปลี่ยนแปลงบางส่วนอาจเป็นรูปแบบตามฤดูกาลปกติ",
    "gdp": "อัตราเติบโตของ GDP: อัตราการเติบโตของผลิตภัณฑ์มวลรวมในประเทศ ณ ราคาคงที่ เทียบไตรมาสเดียวกันของปีก่อน จาก สศช. ชุดไม่ปรับฤดูกาล",
    "proxy": "ตัวชี้วัดตัวแทน: ตัวชี้วัดที่เกี่ยวข้องแต่ไม่ใช่ตัวเดียวกับสิ่งที่ต้องการวัด เช่น ผู้ใช้สิทธิว่างงานประกันสังคม ครอบคลุมเฉพาะผู้ประกันตน ไม่ใช่ผู้ว่างงานทั้งประเทศ",
    "corr": "สหสัมพันธ์ ≠ ความเป็นเหตุเป็นผล: ตัวเลขสองชุดเคลื่อนไหวสัมพันธ์กันไม่ได้แปลว่าชุดหนึ่งเป็นสาเหตุของอีกชุด อาจมีปัจจัยอื่นหรือช่วงเวลาพิเศษที่กระทบทั้งคู่",
    "freshness": "ตัวชี้วัดแต่ละตัวมาจากตารางของ สสช. คนละชุดและเผยแพร่ไม่พร้อมกัน บางตัวมีช่องว่างกลางช่วงเพราะตารางต้นทางขัดแย้งกัน ตารางนี้แสดงไตรมาสล่าสุดที่มีค่าจริงของแต่ละตัว ไม่ใช่ไตรมาสที่เลือก",
    "region_break": "สสช. เปลี่ยนการแบ่งภูมิภาคจาก 5 เป็น 7 กลุ่มตั้งแต่ปี 2568 ภาคกลางและภาคใต้ก่อนและหลังช่วงนี้อาจมีขอบเขตไม่เท่ากัน",
}


def info(key: str) -> str:
    """Hover/focus tooltip icon for a glossary term (HTML)."""
    return f'<span class="tip" tabindex="0" data-tip="{html.escape(GLOSSARY[key], quote=True)}">i</span>'


def esc(x) -> str:
    return html.escape(str(x))


def fmt_num(x, digits=0) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{x:,.{digits}f}"


def fmt_signed(x, digits=1, suffix="") -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    arrow = "▲" if x > 0 else ("▼" if x < 0 else "■")
    return f"{arrow} {x:+,.{digits}f}{suffix}"


def kpi_card(label: str, value: str | None, unit: str = "", sub: str = "", tip: str | None = None,
             source: str = "", na_reason: str | None = None, stats: list[tuple[str, str]] | None = None) -> str:
    """Return card HTML. When ``value`` is None the reason is shown instead of a number.

    ``stats`` = [(name, value_text)] drawn under a divider line, values in bold.
    """
    tip_html = info(tip) if tip else ""
    if value is None:
        body = f'<div class="kpi-na">ข้อมูลไม่เพียงพอสำหรับคำนวณตัวชี้วัดนี้</div><div class="kpi-sub">{esc(na_reason or "")}</div>'
    else:
        body = (f'<div class="kpi-value">{esc(value)}<span class="kpi-unit">{esc(unit)}</span></div>'
                f'<div class="kpi-sub">{sub}</div>')
    if stats:
        rows = "".join(f'<div><span class="k">{esc(k)}:</span> <b>{esc(v)}</b></div>' for k, v in stats)
        body += f'<div class="kpi-divider"></div><div class="kpi-stats">{rows}</div>'
    src = f'<div class="kpi-src">{esc(source)}</div>' if source else ""
    return f'<div class="card" title="{esc(source)}"><div class="kpi-label">{esc(label)} {tip_html}</div>{body}{src}</div>'


def notice(kind: str, text: str, title: str | None = None, brief: str | None = None) -> None:
    """kind: info | warn | err. Prefix text keeps meaning without colour.

    The screen stays light: an info note is folded behind its title; with ``brief`` a warning/error shows
    one short line and keeps the full text one tap away.
    """
    prefix = {"info": "หมายเหตุ", "warn": "ข้อควรระวัง", "err": "ข้อผิดพลาด"}[kind]
    t = title or prefix
    if brief is not None:
        st.markdown(f'<div class="notice {kind}"><b>{esc(t)}</b>{brief}</div>', unsafe_allow_html=True)
        with st.expander("ดูรายละเอียด"):
            st.markdown(text, unsafe_allow_html=True)
        return
    if kind == "info":
        with st.expander(t, icon=":material/info:"):
            st.markdown(text, unsafe_allow_html=True)
        return
    st.markdown(f'<div class="notice {kind}"><b>{esc(t)}</b>{text}</div>', unsafe_allow_html=True)


def empty_state(reason: str, kind: str = "warn") -> None:
    """Where a chart has no trustworthy data: the puzzled mascot and the reason (nothing is estimated)."""
    from dashboard import mascot

    st.markdown(f'<div class="empty-card {kind}"><div class="empty-char">{mascot.unsure3d()}</div>'
                f'<div><b>ไม่สามารถแสดงข้อมูลนี้</b> {esc(reason)}</div></div>', unsafe_allow_html=True)


def section_title(text: str, tip: str | None = None) -> None:
    st.markdown(f'<div class="section-title">{esc(text)} {info(tip) if tip else ""}</div>', unsafe_allow_html=True)


def _fmt_conflict_value(v: float, unit: str) -> str:
    if unit == "บาท":
        return f"{v:,.0f} บาท"
    if unit == "พันคน":
        return f"{v:,.1f} พันคน"
    return f"{v:,.2f}{unit}"


def conflict_table_html(rows: list[dict], period_label) -> str:
    """The quarters left out because the NSO tables disagree: what each table says, how far apart they are, and why the quarter is not shown."""
    body = []
    for r in rows:
        vals = "<br>".join(f"{esc(k)}: <b>{esc(_fmt_conflict_value(v, r.get('unit', '')))}</b>" for k, v in r.get("values", {}).items())
        gap = r.get("gap")
        gap_txt = "—" if gap is None else f"{gap:,.2f} {r.get('gap_unit', '')}".strip()
        body.append(f"<tr><td>{esc(period_label(r['period_idx']))}</td><td>{vals}</td><td>{esc(gap_txt)}</td><td>{esc(r.get('reason', ''))}</td></tr>")
    return ('<table class="cmp-t cf-t"><thead><tr><th>ไตรมาส</th><th>ค่าที่แต่ละตารางของ สสช. ให้</th><th>ต่างกัน</th><th>เหตุผลที่ไม่แสดงค่า</th></tr></thead><tbody>'
            + "".join(body) + "</tbody></table>")


def conflict_box(rows: list[dict], period_label, lo: int | None = None, hi: int | None = None, what: str = "") -> None:
    """A short sentence naming the quarters that are blank on the chart and why, with the details in an open table."""
    rows = [r for r in rows if (lo is None or r["period_idx"] >= lo) and (hi is None or r["period_idx"] <= hi)]
    if not rows:
        return
    names = ", ".join(period_label(r["period_idx"]) for r in rows[:6]) + (" …" if len(rows) > 6 else "")
    st.markdown(f'<div class="cf-note"><b>แถบสีเทาในกราฟ = ไม่แสดงค่า{esc(what)}</b> เพราะตารางต้นทางของ สสช. ขัดแย้งกันเอง ({len(rows)} ไตรมาส: {esc(names)}) '
                "ระบบไม่เลือกค่าเองและไม่ประมาณค่าแทน</div>", unsafe_allow_html=True)
    with st.expander("ดูว่าอะไรขัดแย้งกัน (ค่าของแต่ละตาราง)", expanded=False):
        st.markdown(conflict_table_html(rows, period_label), unsafe_allow_html=True)


def chart_caption(source: str, period: str, unit: str, formula: str = "", limits: str = "", url: str | None = None) -> None:
    """The six trust questions: source / period / unit / formula / limits / link."""
    parts = [f"<b>แหล่งที่มา:</b> {esc(source)}", f"<b>ช่วงเวลา:</b> {esc(period)}", f"<b>หน่วย:</b> {esc(unit)}"]
    if formula:
        parts.append(f"<b>วิธีคำนวณ:</b> {esc(formula)}")
    if limits:
        parts.append(f"<b>ข้อจำกัด:</b> {esc(limits)}")
    if url:
        parts.append(f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">เปิดแหล่งข้อมูลต้นทาง ↗</a>')
    with st.popover("ที่มา · วิธีคำนวณ · ข้อจำกัด", icon=":material/info:"):
        st.markdown('<div class="caption">' + " · ".join(parts) + "</div>", unsafe_allow_html=True)


def period_range_text(df: pd.DataFrame) -> str:
    if df is None or len(df) == 0:
        return "—"
    d = df.sort_values("period_idx")
    return f"{d['period_label'].iloc[0]} ถึง {d['period_label'].iloc[-1]}"


def csv_bytes(df: pd.DataFrame) -> bytes:
    """CSV with UTF-8 BOM so Excel on Windows shows Thai correctly."""
    return df.to_csv(index=False).encode("utf-8-sig")


def callout(title: str, text_html: str) -> None:
    """Amber key-finding box at the top of a page. ``text_html`` must already be escaped."""
    st.markdown(f'<div class="callout"><b>{esc(title)}</b> {text_html}</div>', unsafe_allow_html=True)
