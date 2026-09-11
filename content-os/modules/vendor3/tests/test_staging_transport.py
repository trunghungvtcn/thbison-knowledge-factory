"""Mock transport tests for staging preflight (G6)."""
from __future__ import annotations

import json

import pytest

from app.staging_preflight import PreflightClosed, StagingClient, TransportError, run_preflight


MANIFEST = {
    "databases": [
        {"name": "Evidence Sources", "data_source_id": "c80fbe3f-22e6-8329-9dd6-875fb67a3755"},
        {"name": "Product Attributes", "data_source_id": "e51fbe3f-22e6-82e8-8831-07a909bdba1a"},
    ]
}


class Scripted:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def request(self, method, url, headers, body=None):
        self.calls.append((method, url, "authorization" in {k.lower() for k in headers}))
        item = self.script.pop(0)
        status = item["status"]
        raw = json.dumps(item.get("json", {})).encode()
        hdrs = {k.lower(): v for k, v in item.get("headers", {}).items()}
        if status >= 400:
            raise TransportError(status, raw.decode(), hdrs)
        return status, hdrs, raw


def test_allowlist_blocks_unknown_ds():
    c = StagingClient(MANIFEST, "tok", transport=Scripted([]))
    with pytest.raises(PreflightClosed):
        c.query_data_source("not-in-allowlist")


def test_pagination_two_pages():
    t = Scripted([
        {"status": 200, "json": {"results": [{"id": "a"}], "has_more": True, "next_cursor": "c2"}},
        {"status": 200, "json": {"results": [{"id": "b"}], "has_more": False}},
    ])
    c = StagingClient(MANIFEST, "tok", transport=t, enabled=True)
    rows = c.paginate("c80fbe3f-22e6-8329-9dd6-875fb67a3755")
    assert [r["id"] for r in rows] == ["a", "b"]
    assert len(t.calls) == 2


def test_401_not_ready():
    t = Scripted([{"status": 401, "json": {"message": "no"}}])
    c = StagingClient(MANIFEST, "tok", transport=t, enabled=True)
    with pytest.raises(TransportError) as ei:
        c.query_data_source("c80fbe3f-22e6-8329-9dd6-875fb67a3755")
    assert ei.value.status == 401
    assert c.classify(401) == "AUTH_DENIED"


def test_429_retry_after():
    t = Scripted([{"status": 429, "json": {}, "headers": {"Retry-After": "7"}}])
    c = StagingClient(MANIFEST, "tok", transport=t)
    with pytest.raises(TransportError):
        c.query_data_source("c80fbe3f-22e6-8329-9dd6-875fb67a3755")
    assert c.requests[-1]["retry_after"] == "7"
    assert c.requests[-1]["error"] == "RATE_LIMITED"


def test_timeout_classified():
    class Boom:
        def request(self, *a, **k):
            raise TransportError(598, "timeout")

    c = StagingClient(MANIFEST, "tok", transport=Boom())
    with pytest.raises(TransportError):
        c.query_data_source("c80fbe3f-22e6-8329-9dd6-875fb67a3755")
    assert c.requests[-1]["error"] == "TIMEOUT"


def test_parent_verification():
    c = StagingClient(MANIFEST, "tok", transport=Scripted([]))
    page = {"parent": {"data_source_id": "c80fbe3f-22e6-8329-9dd6-875fb67a3755"}}
    assert c.parent_ok(page, "c80fbe3f-22e6-8329-9dd6-875fb67a3755")
    assert not c.parent_ok({"parent": {"data_source_id": "prod-other"}}, "c80fbe3f-22e6-8329-9dd6-875fb67a3755")


def test_run_preflight_blocked_access(monkeypatch, tmp_path):
    monkeypatch.delenv("STAGING_NOTION_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_STAGING_TOKEN", raising=False)
    monkeypatch.delenv("STAGING_TOKEN", raising=False)
    code, report = run_preflight(MANIFEST, str(tmp_path / "o.json"))
    assert code == 2
    assert report["status"] == "BLOCKED_ACCESS"


def test_run_preflight_blocked_opt_in(monkeypatch, tmp_path):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "secret-value")
    monkeypatch.setenv("STAGING_ENABLED", "false")
    code, report = run_preflight(MANIFEST, str(tmp_path / "o.json"))
    assert code == 3
    assert report["status"] == "BLOCKED_OPT_IN"
    text = (tmp_path / "o.json").read_text()
    assert "secret-value" not in text
