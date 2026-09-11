from tests.test_preflight_r4 import Script, schema, query, page, _run, _expected
from app.staging_preflight import run_preflight
import json


def test_expected_b_provider_a_target_a_fails(tmp_path):
    t = Script()
    for ds in ("ds-a", "ds-b"):
        t.queue(schema(ds, dest="ds-a"))
        t.queue(query(ds, "target-a"))
        t.queue(page("target-a", "ds-a"))
    r = _run(t, tmp_path)  # expected dest B
    assert r["status"] != "PREFLIGHT_MOCK_OK"
    assert any(e["class"] == "SCHEMA_DRIFT" for e in r["errors"])


def test_expected_b_provider_b_target_b_pass(tmp_path):
    t = Script()
    for ds in ("ds-a", "ds-b"):
        t.queue(schema(ds, dest="ds-b"))
        t.queue(query(ds, "t-ok"))
        t.queue(page("t-ok", "ds-b"))
    r = _run(t, tmp_path)
    assert r["status"] == "PREFLIGHT_MOCK_OK"


def test_missing_expected_pin_blocked(tmp_path):
    t = Script()
    t.queue(schema("ds-a", dest="ds-b"))
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"databases": [{"name": "A", "data_source_id": "ds-a"}, {"name": "B", "data_source_id": "ds-b"}]}))
    r = run_preflight(manifest_path=man, transport=t, live=False)
    assert r["status"] == "BLOCKED_OWNER_INPUT"
    assert any(e["class"] == "BLOCKED_OWNER_INPUT" for e in r["errors"])


def test_missing_expected_property(tmp_path):
    t = Script()
    t.queue(schema("ds-a", dest="ds-b"))
    exp = {"ds-a": {"id": "ds-a", "properties": {"Other": {"id": "x", "type": "title"}}},
           "ds-b": {"id": "ds-b", "properties": {"Link": {"id": "rel-id", "type": "relation", "relation": {"data_source_id": "ds-b"}}}}}
    r = _run(t, tmp_path, expected=exp)
    assert any(e["class"] == "SCHEMA_DRIFT" for e in r["errors"])
