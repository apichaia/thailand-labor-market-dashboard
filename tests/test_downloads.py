import json

import pytest
import requests

import config
from data_processing import pipeline
from data_sources import downloader as dl
from data_sources import http_client as hc

SPEC = config.SOURCES_BY_KEY["nso_u_region"]


class FakeResp:
    def __init__(self, status=200, content=b"year,quarter\n2567,1\n", headers=None, url="http://x"):
        self.status_code, self.content, self.headers, self.url = status, content, headers or {"content-type": "text/csv"}, url


class FakeSession:
    """Test double for requests.Session (no real network in unit tests)."""

    def __init__(self, responder):
        self.responder, self.calls = responder, 0

    def request(self, *a, **k):
        self.calls += 1
        r = self.responder(self.calls)
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(hc.time, "sleep", lambda s: None)


def test_connection_error_is_network_error():
    s = FakeSession(lambda n: requests.ConnectionError("down"))
    with pytest.raises(hc.NetworkError):
        hc.fetch_bytes("http://x", session=s, retries=1)
    assert s.calls == 2


def test_http_error_status_is_network_error_with_waf_hint():
    s = FakeSession(lambda n: FakeResp(status=418, content=b"blocked"))
    with pytest.raises(hc.NetworkError) as e:
        hc.fetch_bytes("http://x", session=s, retries=0)
    assert "418" in str(e.value)


def test_html_instead_of_csv_is_content_error():
    s = FakeSession(lambda n: FakeResp(content=b"<!DOCTYPE html><html>blocked</html>"))
    with pytest.raises(hc.ContentError):
        hc.fetch_bytes("http://x", session=s, retries=0)


def test_empty_body_is_content_error():
    with pytest.raises(hc.ContentError):
        hc.check_content(b"", "csv")


def test_xlsx_signature_checked():
    with pytest.raises(hc.ContentError):
        hc.check_content(b"not a zip", "xlsx")


def test_retry_then_success():
    s = FakeSession(lambda n: FakeResp(status=503) if n == 1 else FakeResp())
    assert hc.fetch_bytes("http://x", session=s, retries=2).status == 200


def test_failed_refresh_keeps_previous_cache_and_records_error(tmp_path):
    raw = tmp_path / "raw"
    good = FakeSession(lambda n: FakeResp(content=b"year,quarter\n2567,1\n"))
    r1 = dl.download_source_data(SPEC, raw_dir=raw, session=good)
    assert r1.ok
    path = dl.raw_path(SPEC, raw)
    before = path.read_bytes()
    bad = FakeSession(lambda n: requests.ConnectionError("down"))
    r2 = dl.download_source_data(SPEC, raw_dir=raw, session=bad)
    assert not r2.ok and r2.error_kind == "network" and r2.used_cache
    assert path.read_bytes() == before  # cache untouched
    m = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))[SPEC.key]
    assert m["last_attempt_ok"] is False and m["last_success_at"]


def test_failed_content_does_not_overwrite_cache(tmp_path):
    raw = tmp_path / "raw"
    dl.download_source_data(SPEC, raw_dir=raw, session=FakeSession(lambda n: FakeResp()))
    path = dl.raw_path(SPEC, raw)
    before = path.read_bytes()
    r = dl.download_source_data(SPEC, raw_dir=raw, session=FakeSession(lambda n: FakeResp(content=b"<html>x</html>")))
    assert not r.ok and r.error_kind == "content" and path.read_bytes() == before


def test_status_never_fresh_after_failed_attempt(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    monkeypatch.setattr(config, "DATA_RAW", raw)
    manifest_path = raw / "manifest.json"
    dl.download_source_data(SPEC, raw_dir=raw, session=FakeSession(lambda n: FakeResp()))
    assert dl.source_status(SPEC, dl.load_manifest(manifest_path))["state"] == "fresh"
    dl.download_source_data(SPEC, raw_dir=raw, session=FakeSession(lambda n: requests.Timeout("t")))
    assert dl.source_status(SPEC, dl.load_manifest(manifest_path))["state"] == "cached_after_failure"


def test_status_missing_when_never_downloaded(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_RAW", tmp_path)
    assert dl.source_status(SPEC, {})["state"] == "missing"


def test_pipeline_with_no_raw_files_is_unusable_and_invents_nothing(tmp_path):
    b = pipeline.build_dashboard_data(raw_dir=tmp_path)
    assert not b.usable and b.tables == {}
    assert all(not a["ok"] for a in b.availability.values())


def test_pipeline_empty_primary_file_is_unusable(tmp_path):
    (tmp_path / "nso_u_region.csv").write_text("", encoding="utf-8")
    b = pipeline.build_dashboard_data(raw_dir=tmp_path)
    assert not b.usable
    assert b.availability["nso_u_region"]["kind"] == "validation"
