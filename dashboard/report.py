"""Plain-text (Markdown) summary report for download."""
from __future__ import annotations

from datetime import datetime

import config
from analytics import metrics
from analytics import selectors as sel_
from data_processing import normalize as nz


def build_summary_markdown(ctx) -> str:
    b, f = ctx.bundle, ctx.filters
    sel = sel_.unemployed_series(b, f)
    lines = ["# ข้อมูลเชิงลึกการว่างงานของประเทศไทย — รายงานสรุป", "",
             f"สร้างเมื่อ: {datetime.now().strftime('%Y-%m-%d %H:%M')}", f"ตัวกรองที่ใช้: {f.describe()}", ""]
    idx = sel_.kpi_period(sel, f)
    if idx is None:
        lines.append("ข้อมูลไม่เพียงพอสำหรับคำนวณตัวชี้วัดภายใต้ตัวกรองนี้")
    else:
        u = metrics.kpi_snapshot(sel.data, "u_k", idx)
        r = metrics.kpi_snapshot(sel.data, "rate_pct", idx)
        lines += [f"## ตัวชี้วัด ณ {nz.period_label(idx // 4, idx % 4 + 1)}",
                  f"- จำนวนผู้ว่างงาน: {u['value'] * 1000:,.0f} คน",
                  "- เทียบไตรมาสก่อน (เทียบไตรมาสก่อน): " + (f"{u['qoq_abs'] * 1000:+,.0f} คน ({u['qoq_pct']:+.1f}%)" if not u["qoq_reason"] else "ข้อมูลไม่เพียงพอ — " + u["qoq_reason"]),
                  "- เทียบไตรมาสเดียวกันของปีก่อน: " + (f"{u['yoy_abs'] * 1000:+,.0f} คน ({u['yoy_pct']:+.1f}%)" if not u["yoy_reason"] else "ข้อมูลไม่เพียงพอ — " + u["yoy_reason"]),
                  "- อัตราการว่างงาน: " + (f"{r['value']:.2f}%" if r["value"] == r["value"] else "ข้อมูลไม่เพียงพอสำหรับคำนวณตัวชี้วัดนี้"),
                  f"- แหล่งข้อมูล: {sel.source}", ""]
    lines += ["## สถานะข้อมูล"]
    for s in config.SOURCES:
        m = ctx.manifest.get(s.key, {})
        lines.append(f"- {s.title} ({s.org}): ดึงเมื่อ {m.get('last_success_at', 'ไม่เคยดึงสำเร็จ')} · {s.landing_url}")
    lines += ["", "## ข้อจำกัด",
              "- ข้อมูลมาจากการสำรวจตัวอย่าง ไม่ปรับฤดูกาล; ไม่มีข้อมูลสาเหตุการว่างงานโดยตรงของประชากรทั้งประเทศ",
              "- ความสัมพันธ์กับ GDP ไม่ใช่หลักฐานของความเป็นเหตุเป็นผล"]
    return "\n".join(lines)
