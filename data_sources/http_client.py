"""HTTP helper that separates *network* failures from *content* failures.

The dashboard must be able to tell the user whether a download failed because
the source could not be reached (NetworkError) or because what came back was
not the file we expected (ContentError, e.g. an HTML block page instead of CSV).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

import config

log = logging.getLogger(__name__)


class FetchError(Exception):
    """Base class. ``kind`` is 'network' or 'content'."""

    kind = "fetch"


class NetworkError(FetchError):
    kind = "network"


class ContentError(FetchError):
    kind = "content"


@dataclass
class FetchResult:
    content: bytes
    status: int
    content_type: str
    url: str
    elapsed_s: float


def check_content(content: bytes, expect: str) -> None:
    """Raise ContentError if ``content`` does not look like the expected type."""
    if not content:
        raise ContentError("ไฟล์ที่ได้รับว่างเปล่า")
    head = content[:512].lstrip().lower()
    if expect in ("csv", "json") and (head.startswith(b"<!doctype") or head.startswith(b"<html")):
        raise ContentError("แหล่งข้อมูลตอบกลับเป็นหน้าเว็บ HTML แทนไฟล์ข้อมูล (อาจถูกบล็อกหรือ URL เปลี่ยน)")
    if expect == "xlsx" and not content.startswith(b"PK"):
        raise ContentError("ไฟล์ที่ได้รับไม่ใช่รูปแบบ XLSX")
    if expect == "html" and b"<" not in head[:50]:
        raise ContentError("ไม่พบเนื้อหา HTML ในคำตอบ")


def fetch_bytes(
    url: str,
    *,
    expect: str = "csv",
    session: requests.Session | None = None,
    method: str = "GET",
    data: dict | None = None,
    params: dict | None = None,
    timeout=None,
    retries: int | None = None,
) -> FetchResult:
    """GET/POST ``url`` with retries; validate status code and body type."""
    sess = session or requests.Session()
    headers = {"User-Agent": config.USER_AGENT, "Accept": "*/*"}
    timeout = timeout or config.HTTP_TIMEOUT
    retries = config.HTTP_RETRIES if retries is None else retries
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        t0 = time.monotonic()
        try:
            resp = sess.request(method, url, headers=headers, data=data, params=params, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            log.warning("network error on %s (attempt %d/%d): %s", url, attempt + 1, retries + 1, type(exc).__name__)
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
            continue
        except requests.RequestException as exc:
            raise NetworkError(f"คำขอล้มเหลว: {type(exc).__name__}") from exc
        if resp.status_code >= 500 and attempt < retries:
            log.warning("HTTP %s from %s, retrying", resp.status_code, url)
            time.sleep(1.5 * (attempt + 1))
            continue
        if resp.status_code != 200:
            hint = " (เซิร์ฟเวอร์ปฏิเสธคำขอ อาจเป็นการป้องกันบอทของแหล่งข้อมูล)" if resp.status_code in (403, 418) else ""
            raise NetworkError(f"HTTP {resp.status_code}{hint}")
        check_content(resp.content, expect)
        return FetchResult(
            content=resp.content,
            status=resp.status_code,
            content_type=resp.headers.get("content-type", ""),
            url=resp.url,
            elapsed_s=time.monotonic() - t0,
        )
    raise NetworkError(f"เชื่อมต่อแหล่งข้อมูลไม่ได้ ({type(last_exc).__name__ if last_exc else 'unknown'})")
