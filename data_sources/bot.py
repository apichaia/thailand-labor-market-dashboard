"""Bank of Thailand statistics page EC_RL_019 (unemployed who previously worked,
by reason for leaving the last job).

The page is an ASP.NET form. The default view shows only six quarters, so we
submit the same public form a visitor would use to widen the period.
"""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from data_sources.http_client import ContentError, FetchResult, fetch_bytes


def fetch_bot_reasons_html(url: str, from_year_ce: int, to_year_ce: int, session: requests.Session | None = None) -> FetchResult:
    sess = session or requests.Session()
    first = fetch_bytes(url, expect="html", session=sess)
    soup = BeautifulSoup(first.content.decode("utf-8", "replace"), "html.parser")
    hidden = {i.get("name"): i.get("value", "") for i in soup.find_all("input", {"type": "hidden"}) if i.get("name")}
    if "__VIEWSTATE" not in hidden:
        raise ContentError("ไม่พบฟอร์มของหน้า ธปท. (โครงสร้างหน้าเว็บอาจเปลี่ยน)")
    hidden.update(
        {
            "drpPeriod": "QTR",
            "drpFromQuarter": "xxxx03xx",
            "drpFromYear": f"{from_year_ce}xxxx",
            "drpToQuarter": "xxxx12xx",
            "drpToYear": f"{to_year_ce}xxxx",
            "btnSubmit": "Submit",
        }
    )
    res = fetch_bytes(url, expect="html", session=sess, method="POST", data=hidden)
    if b"EC_RL_019" not in res.content:
        raise ContentError("หน้าผลลัพธ์จาก ธปท. ไม่ตรงกับรายงานที่คาดไว้ (EC_RL_019)")
    return res
