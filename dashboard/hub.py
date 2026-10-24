"""The five top-level pages. Each combines the unemployment views with the employment/wage views of the same topic."""
from __future__ import annotations

import streamlit as st

from dashboard import components as ui
from dashboard import labour_page, pages
from dashboard.pages import Ctx

POP_TABS = ["การศึกษา", "เพศ", "กลุ่มอายุ", "จำนวนผู้มีงานทำ"]
REGION_TABS = ["การว่างงานรายภาค", "ค่าจ้างและการมีงานทำรายภาค"]
ECO_TABS = ["ค่าจ้างและการมีงานทำ", "GDP กับการว่างงาน"]
EVIDENCE_TABS = ["หลักฐานสาเหตุการว่างงาน", "แหล่งข้อมูลและวิธีการ"]


def population(ctx: Ctx) -> None:
    b, f = ctx.bundle, ctx.filters
    ui.section_title("กลุ่มประชากร")
    sub = st.radio("มิติ", POP_TABS, horizontal=True, key="nav_pop", label_visibility="collapsed")
    if sub == "การศึกษา":
        pages.demographic_notice()
        pages._edu_tab(b, f)
        ui.section_title("ค่าจ้างและอัตรามีงานทำตามระดับการศึกษา")
        labour_page.group_section(ctx, "การศึกษา")
    elif sub == "เพศ":
        pages.demographic_notice()
        pages._sex_tab(b, f)
    elif sub == "กลุ่มอายุ":
        pages.demographic_notice()
        pages._age_tab(b, f)
    else:
        labour_page.group_section(ctx, "จำนวนผู้มีงานทำ")


def regional(ctx: Ctx) -> None:
    sub = st.radio("มุมมอง", REGION_TABS, horizontal=True, key="nav_region", label_visibility="collapsed")
    if sub == REGION_TABS[0]:
        pages.regional(ctx)
    else:
        ui.section_title("ค่าจ้างและอัตรามีงานทำรายภูมิภาค")
        labour_page.region_section(ctx)


def economy(ctx: Ctx) -> None:
    sub = st.radio("มุมมอง", ECO_TABS, horizontal=True, key="nav_eco", label_visibility="collapsed")
    if sub == ECO_TABS[0]:
        labour_page.national_section(ctx)
    else:
        pages.economic(ctx)


def evidence(ctx: Ctx) -> None:
    sub = st.radio("มุมมอง", EVIDENCE_TABS, horizontal=True, key="nav_evidence", label_visibility="collapsed")
    if sub == EVIDENCE_TABS[0]:
        pages.factors(ctx)
    else:
        pages.methodology(ctx)
