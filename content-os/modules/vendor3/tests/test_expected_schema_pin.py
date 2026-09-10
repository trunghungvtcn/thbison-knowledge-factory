"""R5: trusted expected_schema pin vs provider schema destination."""
from __future__ import annotations

from app.staging_preflight import run_preflight
from tests.test_preflight_verify import ALLOWED, RELATED, Router, schema_ok


def pin(ds, dest):
    return {ds: {"id": ds, "properties": {"Evidence Sources": {"id": "ev", "type": "relation", "relation": {"data_source_id": dest}}}}}


def _env(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "t")
    monkeypatch.setenv("STAGING_ENABLED", "true")


def test_expected_b_provider_b_target_b_pass(monkeypatch):
    _env(monkeypatch)
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED, RELATED),
        ("GET", f"/data_sources/{RELATED}"): {"status": 200, "json": {"object": "data_source", "id": RELATED, "properties": {}}},
        ("POST", f"/data_sources/{RELATED}/query"): {"status": 200, "json": {"results": [], "has_more": False}},
        ("POST", f"/data_sources/{ALLOWED}/query"): {
            "status": 200,
            "json": {"results": [{"id": "row", "parent": {"data_source_id": ALLOWED}, "properties": {"Evidence Sources": {"id": "ev", "type": "relation", "relation": [{"id": "st"}]}}}], "has_more": False},
        },
        ("GET", "/pages/st"): {"status": 200, "json": {"id": "st", "parent": {"data_source_id": RELATED}}},
    }
    man = {
        "databases": [{"name": "A", "data_source_id": ALLOWED}, {"name": "B", "data_source_id": RELATED}],
        "expected_schema": {
            "version": "1",
            "digest": "pin-b",
            "provenance": "owner-fixture",
            "databases": pin(ALLOWED, RELATED),
        },
    }
    code, r = run_preflight(man, transport=Router(routes))
    assert code == 0
    assert r["status"] == "READ_OK"
    assert r["verified"] is True


def test_expected_b_provider_a_target_a_fail(monkeypatch):
    _env(monkeypatch)
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED, ALLOWED),
        ("POST", f"/data_sources/{ALLOWED}/query"): {
            "status": 200,
            "json": {"results": [{"id": "row", "parent": {"data_source_id": ALLOWED}, "properties": {"Evidence Sources": {"id": "ev", "type": "relation", "relation": [{"id": "ta"}]}}}], "has_more": False},
        },
        ("GET", "/pages/ta"): {"status": 200, "json": {"id": "ta", "parent": {"data_source_id": ALLOWED}}},
    }
    man = {
        "databases": [{"name": "A", "data_source_id": ALLOWED}, {"name": "B", "data_source_id": RELATED}],
        "expected_schema": pin(ALLOWED, RELATED),
    }
    code, r = run_preflight(man, transport=Router(routes))
    assert code != 0
    assert r["verified"] is False
    assert r["status"] == "SCHEMA_DRIFT"
    assert r["status"] != "READ_OK"


def test_missing_pin_not_verified(monkeypatch):
    _env(monkeypatch)
    routes = {
        ("GET", f"/data_sources/{ALLOWED}"): schema_ok(ALLOWED, RELATED),
        ("GET", f"/data_sources/{RELATED}"): {"status": 200, "json": {"object": "data_source", "id": RELATED, "properties": {}}},
        ("POST", f"/data_sources/{RELATED}/query"): {"status": 200, "json": {"results": [], "has_more": False}},
        ("POST", f"/data_sources/{ALLOWED}/query"): {
            "status": 200,
            "json": {"results": [{"id": "row", "parent": {"data_source_id": ALLOWED}, "properties": {"Evidence Sources": {"id": "ev", "type": "relation", "relation": [{"id": "st"}]}}}], "has_more": False},
        },
        ("GET", "/pages/st"): {"status": 200, "json": {"id": "st", "parent": {"data_source_id": RELATED}}},
    }
    code, r = run_preflight({"databases": [{"name": "A", "data_source_id": ALLOWED}, {"name": "B", "data_source_id": RELATED}]}, transport=Router(routes))
    assert r["verified"] is False
    assert r["status"] == "BLOCKED_OWNER_INPUT"
    assert code != 0
