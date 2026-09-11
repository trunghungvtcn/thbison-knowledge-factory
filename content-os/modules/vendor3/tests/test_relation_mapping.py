"""R4 matrix: relation target must match schema-mapped DS, not merely allowlist."""
from __future__ import annotations

import pytest

from app.staging_preflight import run_preflight
from tests.test_preflight_verify import ALLOWED, RELATED, Router, schema_ok

MANIFEST = {"databases": [{"name": "A", "data_source_id": ALLOWED}, {"name": "B", "data_source_id": RELATED}]}


def _env(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "t")
    monkeypatch.setenv("STAGING_ENABLED", "true")


def test_correct_relation_pass(monkeypatch):
    _env(monkeypatch)
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED, RELATED),
        ("GET", f"/data_sources/{RELATED}"): schema_ok(RELATED, RELATED),
        ("POST", f"/data_sources/{ALLOWED}/query"): {
            "status": 200,
            "json": {"results": [{"id": "row", "parent": {"data_source_id": ALLOWED}, "properties": {"Evidence Sources": {"id": "ev", "type": "relation", "relation": [{"id": "st-page"}]}}}], "has_more": False},
        },
        ("POST", f"/data_sources/{RELATED}/query"): {"status": 200, "json": {"results": [{"id": "brow", "parent": {"data_source_id": RELATED}, "properties": {"Evidence Sources": {"id": "ev", "type": "relation", "relation": [{"id": "st-page"}]}}}], "has_more": False}},
        ("GET", "/pages/st-page"): {"status": 200, "json": {"id": "st-page", "parent": {"data_source_id": RELATED}}},
    }
    man = dict(MANIFEST)
    man["expected_schema"] = {
        ALLOWED: {"id": ALLOWED, "properties": {"Evidence Sources": {"id": "ev", "type": "relation", "relation": {"data_source_id": RELATED}}}},
        RELATED: {"id": RELATED, "properties": {"Evidence Sources": {"id": "ev", "type": "relation", "relation": {"data_source_id": RELATED}}}},
    }
    code, r = run_preflight(man, transport=Router(routes))
    assert code == 0
    assert r["status"] == "READ_OK"
    assert r["verified"] is True


def test_wrong_target_in_allowlist_fail(monkeypatch):
    _env(monkeypatch)
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED, RELATED),
        ("GET", f"/data_sources/{RELATED}"): schema_ok(RELATED, RELATED),
        ("POST", f"/data_sources/{ALLOWED}/query"): {
            "status": 200,
            "json": {"results": [{"id": "row", "parent": {"data_source_id": ALLOWED}, "properties": {"Evidence Sources": {"id": "ev", "type": "relation", "relation": [{"id": "target-a"}]}}}], "has_more": False},
        },
        ("POST", f"/data_sources/{RELATED}/query"): {"status": 200, "json": {"results": [], "has_more": False}},
        ("GET", "/pages/target-a"): {"status": 200, "json": {"id": "target-a", "parent": {"data_source_id": ALLOWED}}},
    }
    code, r = run_preflight(MANIFEST, transport=Router(routes))
    assert code != 0
    assert r["verified"] is False
    assert r["status"] == "WRONG_RELATION_TARGET"
    assert r["status"] != "READ_OK"


def test_outside_allowlist_fail(monkeypatch):
    _env(monkeypatch)
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED, RELATED),
        ("POST", f"/data_sources/{ALLOWED}/query"): {
            "status": 200,
            "json": {"results": [{"id": "row", "parent": {"data_source_id": ALLOWED}, "properties": {"Evidence Sources": {"id": "ev", "type": "relation", "relation": [{"id": "prod"}]}}}], "has_more": False},
        },
        ("GET", "/pages/prod"): {"status": 200, "json": {"id": "prod", "parent": {"data_source_id": "production-ds"}}},
    }
    _, r = run_preflight({"databases": [{"name": "A", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert r["status"] == "BLOCKED_STAGING_RELATIONS"
    assert r["verified"] is False


def test_missing_schema_property_fail(monkeypatch):
    _env(monkeypatch)
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): {"status": 200, "json": {"object": "data_source", "id": ALLOWED}},
        ("POST", f"/data_sources/{ALLOWED}/query"): {"status": 200, "json": {"results": [], "has_more": False}},
    }
    _, r = run_preflight({"databases": [{"name": "A", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert r["status"] == "SCHEMA_DRIFT"


def test_empty_result_incomplete(monkeypatch):
    _env(monkeypatch)
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED, RELATED),
        ("POST", f"/data_sources/{ALLOWED}/query"): {"status": 200, "json": {"results": [], "has_more": False}},
    }
    code, r = run_preflight({"databases": [{"name": "A", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert r["status"] == "INCOMPLETE"
    assert r["verified"] is False
    assert code != 0


def test_truncated_relation_no_cursor(monkeypatch):
    _env(monkeypatch)
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED, RELATED),
        ("POST", f"/data_sources/{ALLOWED}/query"): {
            "status": 200,
            "json": {"results": [{"id": "row", "parent": {"data_source_id": ALLOWED}, "properties": {"Evidence Sources": {"id": "ev", "type": "relation", "relation": [{"id": "st-page"}], "has_more": True}}}], "has_more": False},
        },
        ("GET", "/pages/st-page"): {"status": 200, "json": {"id": "st-page", "parent": {"data_source_id": RELATED}}},
    }
    _, r = run_preflight({"databases": [{"name": "A", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert r["status"] == "MISSING_CURSOR"
    assert r["verified"] is False


def test_malformed_query(monkeypatch):
    _env(monkeypatch)
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED, RELATED),
        ("POST", f"/data_sources/{ALLOWED}/query"): {"status": 200, "json": {"oops": True}},
    }
    _, r = run_preflight({"databases": [{"name": "A", "data_source_id": ALLOWED}]}, transport=Router(routes))
    assert r["status"] == "MALFORMED_RESPONSE"
