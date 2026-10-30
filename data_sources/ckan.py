"""CKAN (data.go.th) metadata access. We only *verify* what exists here."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import requests

import config
from data_sources.http_client import ContentError, FetchError, fetch_bytes

log = logging.getLogger(__name__)


def fetch_dataset_metadata(package_id: str, session: requests.Session | None = None) -> dict:
    """Return the CKAN ``package_show`` result for ``package_id``.

    Raises NetworkError / ContentError (never returns invented metadata).
    """
    res = fetch_bytes(
        f"{config.CKAN_BASE}/package_show", params={"id": package_id}, expect="json", session=session
    )
    try:
        payload = json.loads(res.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContentError("คำตอบจาก CKAN ไม่ใช่ JSON ที่อ่านได้") from exc
    if not payload.get("success") or "result" not in payload:
        raise ContentError(f"CKAN ไม่พบ Dataset '{package_id}'")
    return payload["result"]


def summarize_metadata(pkg: dict) -> dict:
    org = (pkg.get("organization") or {}).get("title")
    return {
        "id": pkg.get("name"),
        "title": pkg.get("title"),
        "organization": org,
        "unit_of_measure": pkg.get("unit_of_measure"),
        "unit_of_multiplier": pkg.get("unit_of_multiplier"),
        "first_year_of_data": pkg.get("first_year_of_data"),
        "last_year_of_data": pkg.get("last_year_of_data"),
        "last_updated_date": pkg.get("last_updated_date"),
        "metadata_modified": pkg.get("metadata_modified"),
        "update_frequency": f"{pkg.get('update_frequency_interval') or ''} {pkg.get('update_frequency_unit') or ''}".strip(),
        "calculation_method": pkg.get("calculation_method"),
        "disaggregate": pkg.get("disaggregate"),
        "resources": [
            {"name": r.get("name"), "format": r.get("format"), "url": r.get("url")}
            for r in pkg.get("resources", [])
        ],
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def resolve_resource_url(package_id: str, fmt: str, session: requests.Session | None = None) -> str | None:
    """Find the newest resource URL of a given format in a CKAN package."""
    try:
        pkg = fetch_dataset_metadata(package_id, session=session)
    except FetchError as exc:
        log.info("cannot resolve %s via CKAN: %s", package_id, exc)
        return None
    cands = [r for r in pkg.get("resources", []) if (r.get("format") or "").upper() == fmt.upper() and r.get("url")]
    if not cands:
        return None
    cands.sort(key=lambda r: r.get("last_modified") or r.get("created") or "")
    return cands[-1]["url"]
