"""Download raw files into data/raw and keep a manifest of every attempt.

Rules enforced here:
* A new download only replaces the cached raw file after it has passed the
  status-code and content checks. A failed refresh never destroys the cache.
* The manifest records *when* data was fetched and whether the last attempt
  succeeded, so the UI never calls cached data "latest" when it is not.
* Raw files are stored exactly as received (no silent edits).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests

import config
from data_sources import bot, ckan
from data_sources.http_client import FetchError, fetch_bytes

log = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    key: str
    ok: bool
    error_kind: str | None = None  # 'network' | 'content'
    error: str | None = None
    used_cache: bool = False
    url: str = ""


@dataclass
class RefreshReport:
    results: list[DownloadResult] = field(default_factory=list)

    @property
    def n_ok(self) -> int:
        return sum(r.ok for r in self.results)

    @property
    def failures(self) -> list[DownloadResult]:
        return [r for r in self.results if not r.ok]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _manifest_file(path: Path | None = None) -> Path:
    return Path(path) if path else config.DATA_RAW / "manifest.json"


def load_manifest(path: Path | None = None) -> dict:
    path = _manifest_file(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        log.error("manifest unreadable: %s", path)
        return {}


def save_manifest(manifest: dict, path: Path | None = None) -> None:
    path = _manifest_file(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def raw_path(spec: config.SourceSpec, raw_dir: Path | None = None) -> Path:
    return (raw_dir or config.DATA_RAW) / f"{spec.key}{spec.extension}"


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(content)
    os.replace(tmp, path)


def download_source_data(
    spec: config.SourceSpec,
    *,
    raw_dir: Path | None = None,
    manifest_path: Path | None = None,
    session: requests.Session | None = None,
) -> DownloadResult:
    """Download one source; update raw file + manifest. Never raises on fetch errors."""
    raw_dir = raw_dir or config.DATA_RAW
    if manifest_path is None:
        manifest_path = raw_dir / "manifest.json"  # always next to the raw files it describes
    manifest = load_manifest(manifest_path)
    entry = manifest.get(spec.key, {})
    path = raw_path(spec, raw_dir)
    url = spec.effective_url
    try:
        if spec.resolve_via_ckan and spec.ckan_package and f"TUI_URL_{spec.key.upper()}" not in os.environ:
            resolved = ckan.resolve_resource_url(spec.ckan_package, spec.resolve_via_ckan, session=session)
            if resolved:
                url = resolved
        if spec.kind == "bot_html":
            res = bot.fetch_bot_reasons_html(url, spec.extra["from_year_ce"], spec.extra["to_year_ce"], session=session)
        else:
            res = fetch_bytes(url, expect={"xlsx": "xlsx", "geojson": "json"}.get(spec.kind, "csv"), session=session)
    except FetchError as exc:
        had_cache = path.exists()
        log.error("download failed for %s [%s]: %s", spec.key, exc.kind, exc)
        entry.update(
            {"last_attempt_at": _now(), "last_attempt_ok": False, "last_error_kind": exc.kind,
             "last_error": str(exc), "url_attempted": url}
        )
        manifest[spec.key] = entry
        save_manifest(manifest, manifest_path)
        return DownloadResult(spec.key, False, exc.kind, str(exc), used_cache=had_cache, url=url)

    _write_atomic(path, res.content)
    now = _now()
    entry = {
        "url": url,
        "filename": path.name,
        "fetched_at": now,
        "last_success_at": now,
        "last_attempt_at": now,
        "last_attempt_ok": True,
        "http_status": res.status,
        "content_type": res.content_type,
        "bytes": len(res.content),
        "sha256": hashlib.sha256(res.content).hexdigest(),
    }
    manifest[spec.key] = entry
    save_manifest(manifest, manifest_path)
    log.info("downloaded %s (%d bytes) from %s", spec.key, len(res.content), url)
    return DownloadResult(spec.key, True, url=url)


def fetch_ckan_metadata(package_ids=None, *, raw_dir: Path | None = None, session=None) -> dict:
    """Fetch CKAN metadata for the verification table (best effort)."""
    raw_dir = raw_dir or config.DATA_RAW
    out_path = raw_dir / "ckan_metadata.json"
    existing = {}
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
    for pid in package_ids or config.CKAN_METADATA_PACKAGES:
        try:
            existing[pid] = ckan.summarize_metadata(ckan.fetch_dataset_metadata(pid, session=session))
        except FetchError as exc:
            log.warning("CKAN metadata for %s unavailable: %s", pid, exc)
            existing.setdefault(pid, {"id": pid, "error": str(exc)})
            existing[pid]["last_error"] = str(exc)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return existing


def refresh_all(*, only: list[str] | None = None, with_metadata: bool = True, session=None) -> RefreshReport:
    """Download every source (or ``only`` those keys). Safe to call repeatedly."""
    report = RefreshReport()
    sess = session or requests.Session()
    for spec in config.SOURCES:
        if only and spec.key not in only:
            continue
        report.results.append(download_source_data(spec, session=sess))
    if with_metadata:
        try:
            fetch_ckan_metadata(session=sess)
        except Exception:  # metadata is optional; never block the dashboard
            log.exception("CKAN metadata refresh failed")
    return report


def source_status(spec: config.SourceSpec, manifest: dict | None = None, now: datetime | None = None) -> dict:
    """Describe freshness of one source for the UI.

    state: 'fresh' (last attempt ok, within threshold) | 'stale' (old but last
    attempt ok) | 'cached_after_failure' | 'missing'.
    """
    manifest = manifest if manifest is not None else load_manifest()
    e = manifest.get(spec.key)
    path = raw_path(spec)
    now = now or datetime.now(timezone.utc)
    if not e or not path.exists() or "last_success_at" not in e:
        return {"key": spec.key, "state": "missing", "fetched_at": None, "age_days": None,
                "error": (e or {}).get("last_error"), "error_kind": (e or {}).get("last_error_kind")}
    fetched = datetime.fromisoformat(e["last_success_at"])
    age = (now - fetched).total_seconds() / 86400
    if e.get("last_attempt_ok") is False:
        state = "cached_after_failure"
    elif age > config.STALE_AFTER_DAYS:
        state = "stale"
    else:
        state = "fresh"
    return {"key": spec.key, "state": state, "fetched_at": fetched, "age_days": age,
            "error": e.get("last_error") if state == "cached_after_failure" else None,
            "error_kind": e.get("last_error_kind") if state == "cached_after_failure" else None}
