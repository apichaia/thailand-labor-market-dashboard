"""ศูนย์วิเคราะห์ตลาดแรงงานไทย (การว่างงาน การมีงานทำ ค่าจ้าง) — Streamlit entry point.

Run:  streamlit run app.py
"""
from __future__ import annotations

import json
import logging
import logging.handlers

import streamlit as st

import config
from analytics import selectors as sel_
from dashboard import components as ui
from dashboard import hub, overview, pages, theme
from dashboard.report import build_summary_markdown
from data_processing import normalize as nz
from data_processing.normalize import EDU_ORDER
from data_processing.pipeline import DataBundle, build_dashboard_data
from data_sources import downloader as dl

st.set_page_config(page_title="ศูนย์วิเคราะห์ตลาดแรงงานไทย", page_icon="📊", layout="wide", initial_sidebar_state="auto")


def _setup_logging() -> None:
    root = logging.getLogger()
    if any(getattr(h, "_tui", False) for h in root.handlers):
        return
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(config.LOG_DIR / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    fh._tui = True  # type: ignore[attr-defined]
    root.addHandler(fh)
    root.setLevel(logging.INFO)


_setup_logging()
st.markdown(theme.CSS + theme.CSS_V2, unsafe_allow_html=True)

REQUIRED = [s.key for s in config.SOURCES if s.required]


# ---------------------------------------------------------------------------
# data loading
# ---------------------------------------------------------------------------


def _signature() -> str:
    m = dl.load_manifest()
    return json.dumps({k: (v.get("sha256"), v.get("last_success_at")) for k, v in sorted(m.items())})


@st.cache_data(show_spinner="กำลังตรวจสอบและประมวลผลข้อมูล…", max_entries=2)
def load_bundle(signature: str) -> DataBundle:  # signature only keys the cache
    return build_dashboard_data()


def _load_ckan() -> dict:
    p = config.DATA_RAW / "ckan_metadata.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except (OSError, json.JSONDecodeError):
        return {}


def do_refresh(only_missing: bool = False) -> list:
    """Download sources; returns list of failures. Keeps old cache on failure."""
    only = None
    if only_missing:
        only = [s.key for s in config.SOURCES if not dl.raw_path(s).exists()]
        if not only:
            return []
    with st.spinner("กำลังดึงข้อมูลจากแหล่งต้นทาง… (อาจใช้เวลาประมาณ 1 นาที)"):
        report = dl.refresh_all(only=only)
    st.cache_data.clear()
    return report.failures


# first visit: fetch whatever has never been downloaded (no fake fallback data)
if "boot_done" not in st.session_state:
    st.session_state["boot_failures"] = do_refresh(only_missing=True)
    st.session_state["boot_done"] = True

manifest = dl.load_manifest()
statuses = {s.key: dl.source_status(s, manifest) for s in config.SOURCES}
bundle = load_bundle(_signature())
ckan_meta = _load_ckan()


def overall_status():
    req = [statuses[k] for k in REQUIRED]
    if any(s["state"] == "missing" for s in req):
        return "err", "ยังไม่มีข้อมูลที่เก็บไว้", "—"
    fetched = [s["fetched_at"] for s in statuses.values() if s["fetched_at"]]
    oldest = min(fetched) if fetched else None
    when = oldest.astimezone().strftime("%d/%m/%Y %H:%M") if oldest else "—"
    if any(s["state"] == "cached_after_failure" for s in statuses.values()):
        return "warn", "ดึงข้อมูลใหม่ไม่สำเร็จ ใช้ข้อมูลที่เก็บไว้", when
    if any(s["state"] == "stale" for s in statuses.values()):
        return "warn", f"ข้อมูลเก่ากว่า {config.STALE_AFTER_DAYS} วัน", when
    return "ok", "เชื่อมต่อแหล่งข้อมูลแล้ว", when


kind, status_text, fetched_when = overall_status()

PAGES = ["ภาพรวม", "ภูมิภาค", "กลุ่มแรงงาน"]

# ---------------------------------------------------------------------------
# filter state (kept in session_state; defaults are filled once the data is known)
# ---------------------------------------------------------------------------

nat = bundle.get("national") if bundle.usable else None
years = sorted(nat["year_be"].unique().tolist()) if nat is not None and len(nat) else []
regions = sel_.all_regions(bundle) if bundle.usable else []
ALL_YEARS = "ทุกปี"
DEFAULTS = {"f_year": years[-1] if years else None, "f_quarters": [1, 2, 3, 4],
            "f_regions": [], "f_sex": "ทั้งหมด", "f_edus": []}
for k, v_ in DEFAULTS.items():
    if v_ is not None:
        st.session_state.setdefault(k, v_)


def _reset():
    for k, v_ in DEFAULTS.items():
        if v_ is not None:
            st.session_state[k] = v_


def _current_filters() -> sel_.Filters:
    yr = st.session_state.get("f_year", DEFAULTS["f_year"])
    y0, y1 = (years[0], years[-1]) if (yr in (None, ALL_YEARS) and years) else (yr, yr)
    sex = st.session_state.get("f_sex", "ทั้งหมด")
    return sel_.Filters(
        year_min=y0 or 0, year_max=y1 or 0, quarters=tuple(st.session_state.get("f_quarters") or [1, 2, 3, 4]),
        regions=tuple(st.session_state.get("f_regions", [])), sexes=() if sex in (None, "ทั้งหมด") else (sex,),
        edus=tuple(st.session_state.get("f_edus", [])))


# ---------------------------------------------------------------------------
# sidebar: logo + filters + tools
# ---------------------------------------------------------------------------

filters_now = _current_filters()

with st.sidebar:
    st.markdown('<div class="logo"><div class="mark">📊</div><div><div class="t1">LABOR<br>INSIGHT</div>'
                '<div class="t2">วิเคราะห์ตลาดแรงงานไทย</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="side-title">ตัวกรองข้อมูล</div>', unsafe_allow_html=True)
    if bundle.usable:
        with st.container(key="flt_year"):
            st.selectbox("ปี (พ.ศ.)", [ALL_YEARS] + years[::-1], key="f_year", help="เลือกทีละปี การ์ดด้านบนแสดงไตรมาสล่าสุดของปีที่เลือก")
        with st.container(key="flt_quarter"):
            st.pills("ไตรมาส", [1, 2, 3, 4], selection_mode="multi", key="f_quarters", format_func=lambda q: f"Q{q}")
        with st.container(key="flt_region"):
            st.pills("ภูมิภาค", regions, selection_mode="multi", key="f_regions", help="ไม่เลือก = ทั่วประเทศ")
        with st.container(key="flt_sex"):
            st.segmented_control("เพศ", ["ทั้งหมด", "ชาย", "หญิง"], key="f_sex")
        with st.container(key="flt_edu"):
            st.multiselect("ระดับการศึกษา", EDU_ORDER, key="f_edus", placeholder="ทั้งหมด")
        with st.container(key="side_reset"):
            st.button("↺ รีเซ็ตตัวกรองทั้งหมด", on_click=_reset, width="stretch")
        st.caption("กราฟตามตัวกรองเท่าที่มีตารางต้นทางรองรับ (ภาค/เพศ/การศึกษาร่วมกันใช้ได้ตั้งแต่ 2561) · กราฟที่ใช้ไม่ได้จะบอกไว้ใต้กราฟ")
    area = "ทั่วประเทศ" if not filters_now.regions else ", ".join(filters_now.regions)
    period_txt = ("—" if not filters_now.year_min else (f"พ.ศ. {filters_now.year_min}" if filters_now.year_min == filters_now.year_max else f"พ.ศ. {filters_now.year_min} – {filters_now.year_max}"))
    dot = {"ok": "🟢", "warn": "🟠", "err": "🔴"}[kind]
    rows = [("📅", "ช่วงข้อมูล", period_txt), ("📍", "พื้นที่ศึกษา", area), ("🗄️", "อัปเดตล่าสุด", fetched_when), (dot, "สถานะข้อมูล", status_text)]
    st.markdown('<div class="info-box">' + "".join(
        f'<div class="ir"><span class="ic">{ic}</span><span><span class="k">{ui.esc(k)}</span><span class="v">{ui.esc(v)}</span></span></div>' for ic, k, v in rows)
        + '<div class="ir src"><span class="ic">🧾</span><span><span class="k">แหล่งข้อมูล</span><span class="v">สสช. (สำรวจภาวะการทำงานของประชากร) · สศช. · ธปท. · สำนักงานประกันสังคม</span></span></div></div>',
        unsafe_allow_html=True)
    t1, t2 = st.columns(2, gap="small")
    with t1:
        if st.button("🔄 รีเฟรช", width="stretch", help="ดึงข้อมูลใหม่จากแหล่งต้นทาง หากล้มเหลวจะคงข้อมูลเดิมไว้"):
            st.session_state["boot_failures"] = do_refresh()
            st.rerun()
    report_slot = t2.empty()

filters = _current_filters()
fails = st.session_state.get("boot_failures") or []
ctx = pages.Ctx(bundle=bundle, filters=filters, statuses=statuses, manifest=manifest, ckan=ckan_meta, refresh_failures=fails)
with report_slot:
    st.download_button("⬇ รายงาน", build_summary_markdown(ctx).encode("utf-8"), file_name="labour_market_summary.md", mime="text/markdown",
                       width="stretch", help="ดาวน์โหลดรายงานสรุป (.md) ตามตัวกรองปัจจุบัน")


@st.dialog("ที่มา วิธีการ และหลักฐาน", width="large")
def _sources_dialog() -> None:
    hub.evidence(ctx)


# ---------------------------------------------------------------------------
# hero banner: title, data chips, the three pages
# ---------------------------------------------------------------------------

with st.container(key="hero"):
    h_left, h_right = st.columns([2.1, 1.25], gap="small", vertical_alignment="top")
    with h_left:
        st.markdown('<h1 class="hero-t">ศูนย์วิเคราะห์ตลาดแรงงานไทย</h1>'
                    '<div class="hero-s">วิเคราะห์การจ้างงาน การว่างงาน ค่าจ้าง และสภาวะตลาดแรงงานของไทย ในมิติเวลา ภูมิภาค และกลุ่มประชากร</div>',
                    unsafe_allow_html=True)
    with h_right:
        page = st.radio("เลือกหน้า", PAGES, horizontal=True, key="nav_page", label_visibility="collapsed")
    if st.button("ℹ️ ที่มา วิธีการ และหลักฐาน", key="open_sources"):
        _sources_dialog()

if fails:
    net = [f_ for f_ in fails if f_.error_kind == "network"]
    cont = [f_ for f_ in fails if f_.error_kind == "content"]
    msg = []
    if net:
        msg.append(f"ปัญหาการเชื่อมต่อเครือข่าย {len(net)} แหล่ง: " + "; ".join(sorted({f'{x.key} ({x.error})' for x in net})[:3]))
    if cont:
        msg.append(f"ไฟล์ที่ได้รับไม่ถูกต้อง {len(cont)} แหล่ง: " + "; ".join(sorted({f'{x.key} ({x.error})' for x in cont})[:3]))
    ui.notice("warn", ui.esc(" | ".join(msg)) + " — ระบบคงข้อมูลเดิมไว้ (ถ้ามี) กรุณาตรวจสอบ URL/อินเทอร์เน็ตแล้วกด รีเฟรช อีกครั้ง", "ดึงข้อมูลบางแหล่งไม่สำเร็จ",
              brief=" " + ui.esc(msg[0][:90]) if msg else " ")
val_fail = [k for k, a in bundle.availability.items() if a.get("kind") == "validation"]
if val_fail:
    ui.notice("err", "ข้อมูลที่ดึงมาไม่ผ่านการตรวจสอบคุณภาพ จึงไม่ถูกนำไปคำนวณ: " + ui.esc(", ".join(val_fail)) + " (ดูรายละเอียดที่ปุ่ม ที่มา วิธีการ และหลักฐาน)",
              "ปัญหาด้านคุณภาพข้อมูล (ไม่ใช่ปัญหาเครือข่าย)", brief=" " + ui.esc(", ".join(val_fail)))

if not bundle.usable:
    ui.empty_state("ไม่สามารถเข้าถึงแหล่งข้อมูลต้นทางได้ในขณะนี้ กรุณาตรวจสอบ URL หรือเชื่อมต่อข้อมูลอีกครั้ง "
                   "(ระบบไม่แสดงตัวเลขสมมติแทนข้อมูลจริง) · วิธีแก้ไขดูใน README.md", kind="err")
    st.stop()

# ---------------------------------------------------------------------------
# main content: only the selected page is drawn
# ---------------------------------------------------------------------------

pages.reset_cards()
if page == PAGES[0]:
    overview.home(ctx)
elif page == PAGES[1]:
    hub.regional(ctx)
else:
    hub.population(ctx)
