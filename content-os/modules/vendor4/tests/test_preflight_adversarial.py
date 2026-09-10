from __future__ import annotations

import json
from pathlib import Path

from app.notion_transport import TransportError
from app.staging_preflight import NOTION_VERSION, run_preflight

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "docs/STAGING_ACCESS_MANIFEST.json").read_text())
IDS = [d["data_source_id"] for d in MANIFEST["databases"]]
EVIDENCE_DS = IDS[0]

def pinned_manifest(tmp_path):
    m = json.loads((ROOT / "docs/STAGING_ACCESS_MANIFEST.json").read_text())
    m["expected_schema"] = {
        ds: {
            "id": ds,
            "properties": {
                "Evidence Sources": {"id": "rel-id", "type": "relation", "relation": {"data_source_id": EVIDENCE_DS}},
                "Name": {"type": "title"},
            },
        }
        for ds in IDS
    }
    path = tmp_path / "pinned_manifest.json"
    path.write_text(json.dumps(m))
    return path


class Script:
    def __init__(self):
        self.calls = []
        self.script = []

    def queue(self, item):
        self.script.append(item)

    def request(self, method, url, headers, body=None, timeout=10.0):
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        assert headers.get("Notion-Version") == NOTION_VERSION
        if not self.script:
            raise TransportError("NO_SCRIPT", None, url)
        item = self.script.pop(0)
        if isinstance(item, TransportError):
            raise item
        return item


def schema(ds, rel_name="Evidence Sources"):
    return {
        "status": 200,
        "body": {
            "id": ds,
            "properties": {
                "Name": {"type": "title"},
                rel_name: {"type": "relation", "relation": {"data_source_id": EVIDENCE_DS}},
            },
        },
    }


def query(rows, has_more=False, cursor=None):
    return {"status": 200, "body": {"results": rows, "has_more": has_more, "next_cursor": cursor}}


def row(ds, rid="row1", targets=None, parent=True):
    r = {"id": rid, "properties": {"Evidence Sources": {"type": "relation", "relation": targets or []}}}
    if parent:
        r["parent"] = {"data_source_id": ds, "type": "data_source"}
    return r


def page(pid, parent_ds):
    return {"status": 200, "body": {"id": pid, "parent": {"type": "data_source", "data_source_id": parent_ds}}}


def test_repro_false_success_now_fails_closed(tmp_path):
    t = Script()
    for ds in IDS:
        t.queue(schema(ds))
        t.queue(query([row(ds, targets=[{"id": "production-evidence-page"}], parent=False)]))
    r = run_preflight(manifest_path=pinned_manifest(tmp_path), transport=t, live=False)
    assert r["status"] != "PREFLIGHT_MOCK_OK"
    assert r["status"] in {"CHANGES_REQUIRED", "BLOCKED_STAGING_RELATIONS"}
    assert all(not d.get("relation_targets_verified") for d in r["databases"])
    assert "MISSING_PARENT" in (r.get("reason") or "") or any(e["class"] == "MISSING_PARENT" for e in r["errors"])


def test_correct_row_wrong_target(tmp_path):
    t = Script()
    ds = IDS[2]
    for cur in IDS:
        t.queue(schema(cur))
        if cur == ds:
            t.queue(query([row(cur, targets=[{"id": "prod-page-1"}])]))
            t.queue(page("prod-page-1", "production-parent-ds"))
        else:
            t.queue(query([]))
    r = run_preflight(manifest_path=pinned_manifest(tmp_path), transport=t)
    assert r["status"] == "BLOCKED_STAGING_RELATIONS"
    assert any(e["class"] == "OUTSIDE_ALLOWLIST" for e in r["errors"])


def test_wrong_row_ds(tmp_path):
    t = Script()
    t.queue(schema(IDS[0]))
    t.queue(query([row("some-other-ds", targets=[])]))
    r = run_preflight(manifest_path=pinned_manifest(tmp_path), transport=t)
    assert any(e["class"] == "OUTSIDE_ALLOWLIST" for e in r["errors"])


def test_correct_target_and_pagination(tmp_path):
    t = Script()
    ds = IDS[2]
    for cur in IDS:
        t.queue(schema(cur))
        if cur == ds:
            t.queue(query([row(cur, rid="a", targets=[{"id": "t1"}])], has_more=True, cursor="c2"))
            t.queue(query([row(cur, rid="b", targets=[{"id": "t2"}])], has_more=False))
            t.queue(page("t1", EVIDENCE_DS))
            t.queue(page("t2", EVIDENCE_DS))
        else:
            t.queue(query([]))
    r = run_preflight(manifest_path=pinned_manifest(tmp_path), transport=t)
    assert r["status"] == "PREFLIGHT_INCOMPLETE"
    knowledge = next(d for d in r["databases"] if d["data_source_id"] == ds)
    assert knowledge["pages"] == 2
    assert knowledge["relation_targets_verified"] is True


def test_missing_cursor_fail_closed(tmp_path):
    t = Script()
    t.queue(schema(IDS[0]))
    t.queue(query([row(IDS[0], targets=[])], has_more=True, cursor=None))
    r = run_preflight(manifest_path=pinned_manifest(tmp_path), transport=t)
    assert any(e["class"] == "MALFORMED_RESPONSE" for e in r["errors"])


def test_401_403_429_timeout_classified(tmp_path):
    t = Script()
    t.queue(TransportError("HTTP_ERROR", 401, "no"))
    r = run_preflight(manifest_path=pinned_manifest(tmp_path), transport=t)
    assert r["status"] == "BLOCKED_ACCESS"
    t = Script()
    t.queue(schema(IDS[0]))
    t.queue(TransportError("HTTP_ERROR", 429, "slow"))
    r = run_preflight(manifest_path=pinned_manifest(tmp_path), transport=t)
    assert r["status"] == "RATE_LIMITED"
    t = Script()
    t.queue(schema(IDS[0]))
    t.queue(TransportError("TIMEOUT_OR_NETWORK", None, "t"))
    r = run_preflight(manifest_path=pinned_manifest(tmp_path), transport=t)
    assert r["status"] == "TIMEOUT_OR_NETWORK"


def test_outside_allowlist_not_auth_denied(tmp_path):
    t = Script()
    t.queue(schema(IDS[0]))
    t.queue(query([row("prod-ds")]))
    r = run_preflight(manifest_path=pinned_manifest(tmp_path), transport=t)
    assert any(e["class"] == "OUTSIDE_ALLOWLIST" for e in r["errors"])
    assert all(e["class"] != "AUTH_DENIED" for e in r["errors"])


def test_header_and_path_use_data_sources_2025(tmp_path):
    t = Script()
    t.queue(schema(IDS[0]))
    t.queue(query([]))
    for ds in IDS[1:]:
        t.queue(schema(ds))
        t.queue(query([]))
    run_preflight(manifest_path=pinned_manifest(tmp_path), transport=t)
    assert t.calls[0]["headers"]["Notion-Version"] == "2025-09-03"
    assert "/v1/data_sources/" in t.calls[0]["url"]
    assert t.calls[0]["method"] == "GET"
    assert t.calls[1]["method"] == "POST"
    assert t.calls[1]["url"].endswith("/query")
