"""Adversarial mock preflight: must fail closed, never READ_OK on bad parents/relations."""
from __future__ import annotations

import json

import pytest

from app.staging_preflight import NOTION_VERSION, StagingClient, TransportError, run_preflight

ALLOWED = "allowed-staging"
RELATED = "related-staging"
MANIFEST = {"databases": [{"name": "test", "data_source_id": ALLOWED}, {"name": "rel", "data_source_id": RELATED}]}


class Router:
    """Protocol-shaped Notion mock. Routes by path."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def request(self, method, url, headers, body=None):
        self.calls.append({"method": method, "url": url, "version": headers.get("Notion-Version")})
        path = url.replace("https://api.notion.com/v1", "")
        key = (method, path.split("?")[0])
        item = self.routes.get(key) or self.routes.get(path.split("?")[0])
        if item is None:
            raise TransportError(404, "missing mock", kind="NOT_FOUND")
        if callable(item):
            item = item(method, url, headers, body)
        status = item.get("status", 200)
        hdrs = {k.lower(): v for k, v in item.get("headers", {}).items()}
        raw = json.dumps(item.get("json", {})).encode()
        if status >= 400:
            raise TransportError(status, raw.decode(), hdrs, kind=item.get("kind"))
        return status, hdrs, raw


def schema_ok(ds, target=None):
    tgt = target if target is not None else RELATED
    return {"status": 200, "json": {"object": "data_source", "id": ds, "properties": {"Evidence Sources": {"id": "ev", "type": "relation", "relation": {"data_source_id": tgt}}}}}


def test_repro_wrong_parent_and_prod_relation_not_read_ok(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "mock-test")
    monkeypatch.setenv("STAGING_ENABLED", "true")
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED),
        ("POST", f"/data_sources/{ALLOWED}/query"): {
            "status": 200,
            "json": {
                "results": [{
                    "id": "row",
                    "parent": {"data_source_id": "wrong-parent"},
                    "properties": {"Evidence Sources": {"type": "relation", "relation": [{"id": "production-evidence-page"}]}},
                }],
                "has_more": False,
            },
        },
    }
    code, r = run_preflight({"databases": [{"name": "test", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert code != 0
    assert r["status"] != "READ_OK"
    assert r["verified"] is False
    assert r["status"] in {"WRONG_ROW_DS", "BLOCKED_STAGING_RELATIONS"}


def test_correct_row_wrong_target(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "t")
    monkeypatch.setenv("STAGING_ENABLED", "true")
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED),
        ("POST", f"/data_sources/{ALLOWED}/query"): {
            "status": 200,
            "json": {"results": [{"id": "row", "parent": {"data_source_id": ALLOWED}, "properties": {"Evidence Sources": {"type": "relation", "relation": [{"id": "prod-page"}]}}}], "has_more": False},
        },
        ("GET", "/pages/prod-page"): {"status": 200, "json": {"id": "prod-page", "parent": {"data_source_id": "production-ds"}}},
    }
    code, r = run_preflight({"databases": [{"name": "test", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert r["status"] == "BLOCKED_STAGING_RELATIONS"
    assert r["verified"] is False
    assert code != 0


def test_no_parent(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "t")
    monkeypatch.setenv("STAGING_ENABLED", "true")
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED),
        ("POST", f"/data_sources/{ALLOWED}/query"): {"status": 200, "json": {"results": [{"id": "row", "properties": {}}], "has_more": False}},
    }
    code, r = run_preflight({"databases": [{"name": "t", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert r["status"] == "NO_PARENT"
    assert r["verified"] is False


def test_wrong_row_ds(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "t")
    monkeypatch.setenv("STAGING_ENABLED", "true")
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED),
        ("POST", f"/data_sources/{ALLOWED}/query"): {"status": 200, "json": {"results": [{"id": "row", "parent": {"data_source_id": "other"}}], "has_more": False}},
    }
    _, r = run_preflight({"databases": [{"name": "t", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert r["status"] == "WRONG_ROW_DS"


def test_correct_target_verified(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "t")
    monkeypatch.setenv("STAGING_ENABLED", "true")
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED),
        ("GET", f"/data_sources/{RELATED}"): {"status": 200, "json": {"object": "data_source", "id": RELATED, "properties": {}}},
        ("POST", f"/data_sources/{ALLOWED}/query"): {
            "status": 200,
            "json": {"results": [{"id": "row", "parent": {"data_source_id": ALLOWED}, "properties": {"Evidence Sources": {"type": "relation", "relation": [{"id": "st-page"}]}}}], "has_more": False},
        },
        ("POST", f"/data_sources/{RELATED}/query"): {"status": 200, "json": {"results": [], "has_more": False}},
        ("GET", "/pages/st-page"): {"status": 200, "json": {"id": "st-page", "parent": {"data_source_id": RELATED}}},
    }
    man = dict(MANIFEST)
    man["expected_schema"] = {
        ALLOWED: {"id": ALLOWED, "properties": {"Evidence Sources": {"id": "ev", "type": "relation", "relation": {"data_source_id": RELATED}}}},
        RELATED: {"id": RELATED, "properties": {}},
    }
    code, r = run_preflight(man, transport=Router(routes))
    assert code == 0
    assert r["status"] == "READ_OK"
    assert r["verified"] is True


def test_empty_relations_not_verified(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "t")
    monkeypatch.setenv("STAGING_ENABLED", "true")
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED),
        ("POST", f"/data_sources/{ALLOWED}/query"): {"status": 200, "json": {"results": [{"id": "row", "parent": {"data_source_id": ALLOWED}, "properties": {}}], "has_more": False}},
    }
    code, r = run_preflight({"databases": [{"name": "t", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert code != 0
    assert r["verified"] is False
    assert r["status"] in {"INCOMPLETE", "MISSING_RELATION_PROPERTY"}
    assert r["verified"] is False


def test_pagination_two_pages(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "t")
    monkeypatch.setenv("STAGING_ENABLED", "true")
    qcalls = {"n": 0}

    def query(method, url, headers, body):
        qcalls["n"] += 1
        if qcalls["n"] == 1:
            return {"status": 200, "json": {"results": [{"id": "a", "parent": {"data_source_id": ALLOWED}, "properties": {}}], "has_more": True, "next_cursor": "c2"}}
        return {"status": 200, "json": {"results": [{"id": "b", "parent": {"data_source_id": ALLOWED}, "properties": {}}], "has_more": False}}

    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED),
        ("POST", f"/data_sources/{ALLOWED}/query"): query,
    }
    _, r = run_preflight({"databases": [{"name": "t", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert qcalls["n"] == 2
    assert r["verified"] is False  # empty relations


def test_missing_cursor(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "t")
    monkeypatch.setenv("STAGING_ENABLED", "true")
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED),
        ("POST", f"/data_sources/{ALLOWED}/query"): {"status": 200, "json": {"results": [], "has_more": True}},
    }
    _, r = run_preflight({"databases": [{"name": "t", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert r["status"] == "MISSING_CURSOR"
    assert r["verified"] is False


def test_401(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "t")
    monkeypatch.setenv("STAGING_ENABLED", "true")
    routes = {("GET", f"/data_sources/{ALLOWED}"): {"status": 401, "json": {}}}
    _, r = run_preflight({"databases": [{"name": "t", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert r["status"] == "AUTH_DENIED"


def test_429_retry_after(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "t")
    monkeypatch.setenv("STAGING_ENABLED", "true")
    routes = {("GET", f"/data_sources/{ALLOWED}"): {"status": 429, "json": {}, "headers": {"Retry-After": "5"}}}
    _, r = run_preflight({"databases": [{"name": "t", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert r["status"] == "RATE_LIMITED"
    assert any(x.get("retry_after") == "5" for x in r["requests"])


def test_timeout_kind_precedes_http(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "t")
    monkeypatch.setenv("STAGING_ENABLED", "true")

    class Boom:
        def request(self, *a, **k):
            raise TransportError(598, "timeout", kind="TIMEOUT")

    _, r = run_preflight({"databases": [{"name": "t", "data_source_id": ALLOWED}]}, transport=Boom())
    assert r["status"] == "TIMEOUT"


def test_header_and_path_version():
    c = StagingClient({"databases": [{"name": "t", "data_source_id": ALLOWED}]}, "tok", transport=Router({
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED),
    }))
    c.fetch_schema(ALLOWED)
    assert c.requests[0]["notion_version"] == "2025-09-03"
    assert c.requests[0]["path"] == f"/data_sources/{ALLOWED}"
    assert NOTION_VERSION == "2025-09-03"
    assert "/data_sources/" in c.requests[0]["url"]
