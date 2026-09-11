from __future__ import annotations

import json
from pathlib import Path

from app.notion_transport import TransportError
from app.staging_preflight import run_preflight


class Script:
    def __init__(self):
        self.calls = []
        self.script = []

    def queue(self, item):
        self.script.append(item)

    def request(self, method, url, headers, body=None, timeout=10.0):
        self.calls.append({"method": method, "url": url})
        if not self.script:
            raise TransportError("NO_SCRIPT", None, url)
        item = self.script.pop(0)
        if isinstance(item, TransportError):
            raise item
        return item


def schema(ds, dest="ds-b", prop="Link"):
    return {
        "status": 200,
        "body": {
            "id": ds,
            "object": "data_source",
            "properties": {
                prop: {"id": "rel-id", "type": "relation", "relation": {"data_source_id": dest}}
            },
        },
    }


def query(ds, target="target-1", has_more_rel=False, cursor=None, parent=True):
    row = {
        "id": "row-" + ds,
        "properties": {
            "Link": {
                "id": "rel-id",
                "type": "relation",
                "relation": [{"id": target}] if target else [],
                "has_more": has_more_rel,
                "next_cursor": cursor,
            }
        },
    }
    if parent:
        row["parent"] = {"data_source_id": ds}
    return {"status": 200, "body": {"results": [row], "has_more": False}}


def page(pid, parent_ds):
    return {"status": 200, "body": {"id": pid, "parent": {"data_source_id": parent_ds}}}


def _expected():
    props = {"Link": {"id": "rel-id", "type": "relation", "relation": {"data_source_id": "ds-b"}}}
    return {ds: {"id": ds, "properties": props} for ds in ("ds-a", "ds-b")}

def _run(script, tmp_path, expected=None):
    man = tmp_path / "m.json"
    man.write_text(json.dumps({
        "databases": [{"name": "A", "data_source_id": "ds-a"}, {"name": "B", "data_source_id": "ds-b"}],
        "expected_schema": expected if expected is not None else _expected(),
        "expected_schema_provenance": {"version": "r5-test", "source": "TEST_ONLY"},
    }))
    return run_preflight(manifest_path=man, transport=script, live=False)


def test_correct_relation_pass(tmp_path):
    t = Script()
    for ds in ("ds-a", "ds-b"):
        t.queue(schema(ds, dest="ds-b"))
        t.queue(query(ds, "t-ok"))
        t.queue(page("t-ok", "ds-b"))
    r = _run(t, tmp_path)
    assert r["status"] == "PREFLIGHT_MOCK_OK"
    assert all(d["relation_targets_verified"] for d in r["databases"])


def test_wrong_target_same_allowlist_fails(tmp_path):
    t = Script()
    for ds in ("ds-a", "ds-b"):
        t.queue(schema(ds, dest="ds-b"))
        t.queue(query(ds, "t-a"))
        t.queue(page("t-a", "ds-a"))
    r = _run(t, tmp_path)
    assert r["status"] != "PREFLIGHT_MOCK_OK"
    assert r["status"] == "BLOCKED_STAGING_RELATIONS"
    assert any(e["class"] == "RELATION_TARGET_MISMATCH" for e in r["errors"])


def test_truncated_relation_fails(tmp_path):
    t = Script()
    for ds in ("ds-a", "ds-b"):
        t.queue(schema(ds, dest="ds-b"))
        t.queue(query(ds, "t-ok", has_more_rel=True, cursor=None))
        t.queue(page("t-ok", "ds-b"))
    r = _run(t, tmp_path)
    assert r["status"] != "PREFLIGHT_MOCK_OK"
    assert any(e["class"] == "RELATION_TRUNCATED" for e in r["errors"])


def test_multipage_relation_last_page_wrong(tmp_path):
    t = Script()
    t.queue(schema("ds-a", dest="ds-b"))
    q = query("ds-a", "t1", has_more_rel=True, cursor="c1")
    t.queue(q)
    t.queue({"status": 200, "body": {"results": [{"relation": {"id": "t2"}}], "has_more": False}})
    t.queue(page("t1", "ds-b"))
    t.queue(page("t2", "ds-a"))
    t.queue(schema("ds-b", dest="ds-b"))
    t.queue(query("ds-b", "t1"))
    t.queue(page("t1", "ds-b"))
    r = _run(t, tmp_path)
    assert any(e["class"] == "RELATION_TARGET_MISMATCH" for e in r["errors"])


def test_empty_result_incomplete(tmp_path):
    t = Script()
    for ds in ("ds-a", "ds-b"):
        t.queue(schema(ds))
        t.queue({"status": 200, "body": {"results": [], "has_more": False}})
    r = _run(t, tmp_path)
    assert r["status"] == "PREFLIGHT_INCOMPLETE"
    assert all(d["scope"] == "NOT_APPLICABLE" for d in r["databases"])


def test_schema_id_mismatch(tmp_path):
    t = Script()
    t.queue({"status": 200, "body": {"id": "other", "properties": {}}})
    r = _run(t, tmp_path)
    assert any(e["class"] == "SCHEMA_DRIFT" for e in r["errors"])
