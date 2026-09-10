from copy import deepcopy

from thbison_v6.ledger import Clock
from thbison_v6.staging.preflight import FakeNotionTransport, load_manifest, load_protocol, run_preflight

DS = "c80fbe3f-22e6-8329-9dd6-875fb67a3755"
VALID_SCHEMA = {
    "Name": {"type": "title"},
    "Status": {"type": "select"},
    "Related": {"type": "relation", "relation_destination": "expected-parent-hub"},
}


def _one_ds():
    m = load_manifest()
    m["databases"] = [d for d in m["databases"] if d["data_source_id"] == DS]
    assert m["databases"]
    return m


def _valid_transport():
    t = FakeNotionTransport()
    t.schema[DS] = dict(VALID_SCHEMA)
    return t


def test_auth_failure():
    t = _valid_transport()
    t.auth_ok = False
    out = run_preflight(t, _one_ds(), token="bad")
    assert out["status"] == "BLOCKED_ACCESS"
    assert out["verified"] is False


def test_forbidden_on_schema():
    t = _valid_transport()
    t.forbid = True
    out = run_preflight(t, _one_ds(), token="tok")
    assert out["status"] == "BLOCKED_ACCESS"
    assert out.get("hop") == "schema"


def test_pagination_and_retry():
    t = _valid_transport()
    t.force_429 = 1
    t.pages[DS] = [{"id": "a", "project_id": "proj-lab", "parent": {"data_source_id": DS}} for _ in range(3)]
    clock = Clock()
    out = run_preflight(t, _one_ds(), token="tok", clock=clock)
    assert out["status"] == "PREFLIGHT_OK_FAKE_TRANSPORT"
    assert out["verified"] is False
    assert out["live_calls"] == 0
    assert t.calls >= 3


def test_positive_valid_fixture():
    t = _valid_transport()
    t.pages[DS] = [
        {
            "id": "row-1",
            "parent": {"data_source_id": DS},
            "project_id": "proj-lab",
            "properties": {"Related": {"relation": [{"id": "rel-1"}]}},
        }
    ]
    t.relation_targets["rel-1"] = "expected-parent-hub"
    t.relation_pages["rel-1"] = [{"id": "c1"}, {"id": "c2"}, {"id": "c3"}]
    out = run_preflight(t, _one_ds(), token="tok")
    assert out["status"] == "PREFLIGHT_OK_FAKE_TRANSPORT"
    assert out["verified"] is False
    assert out["protocol_pin"] == "v6-r2-preflight-1"


def test_missing_property_and_type_mismatch():
    t = FakeNotionTransport()
    t.schema[DS] = {"Name": {"type": "rich_text"}}  # Status missing, Name wrong type
    out = run_preflight(t, _one_ds(), token="tok")
    issues = {f["issue"] for f in out["findings"]}
    assert "MISSING_PROPERTY" in issues
    assert "TYPE_MISMATCH" in issues
    assert out["status"] == "DRIFT"
    assert out["verified"] is False


def test_mapping_mismatch():
    t = _valid_transport()
    t.schema[DS]["Related"] = {"type": "relation", "relation_destination": "other-dest"}
    out = run_preflight(t, _one_ds(), token="tok")
    assert any(f["issue"] == "MAPPING_MISMATCH" for f in out["findings"])


def test_schema_drift_extra_property():
    t = _valid_transport()
    t.schema[DS]["Unexpected"] = {"type": "rich_text"}
    out = run_preflight(t, _one_ds(), token="tok")
    assert any(f["issue"] == "SCHEMA_DRIFT" for f in out["findings"])


def test_target_wrong_in_allowlist():
    t = _valid_transport()
    t.pages[DS] = [{"id": "a", "project_id": "proj-lab", "relation_page_id": "rel-1"}]
    t.relation_targets["rel-1"] = "allowlisted-parent"  # in allowlist but not expected hub
    out = run_preflight(t, _one_ds(), token="tok")
    assert any(f["issue"] == "BLOCKED_STAGING_RELATIONS" for f in out["findings"])
    assert out["status"] == "BLOCKED_STAGING_RELATIONS"


def test_outside_allowlist():
    t = _valid_transport()
    t.pages[DS] = [{"id": "a", "project_id": "proj-lab", "relation_page_id": "rel-1"}]
    t.relation_targets["rel-1"] = "random-parent"
    out = run_preflight(t, _one_ds(), token="tok")
    assert any(f["issue"] == "OUTSIDE_ALLOWLIST" for f in out["findings"])


def test_missing_parent():
    t = _valid_transport()
    t.pages[DS] = [{"id": "a", "project_id": "proj-lab", "relation_page_id": "rel-1"}]
    t.relation_targets["rel-1"] = None  # parent page_id None
    # Fake returns parent page_id None
    t.relation_targets["rel-1"] = None
    out = run_preflight(t, _one_ds(), token="tok")
    # json parent page_id None → MISSING_PARENT
    assert any(f["issue"] == "MISSING_PARENT" for f in out["findings"])


def test_wrong_row_parent_ds():
    t = _valid_transport()
    t.pages[DS] = [{"id": "a", "parent": {"data_source_id": "other-ds"}, "project_id": "proj-lab"}]
    out = run_preflight(t, _one_ds(), token="tok")
    assert any(f["issue"] == "WRONG_PARENT_DS" for f in out["findings"])


def test_project_scope_leak_from_properties():
    t = _valid_transport()
    t.pages[DS] = [
        {
            "id": "x",
            "parent": {"data_source_id": DS},
            "properties": {"Project": {"rich_text": [{"plain_text": "other-proj"}]}},
        }
    ]
    out = run_preflight(t, _one_ds(), token="tok", project_id="proj-lab")
    assert any(f["issue"] == "PROJECT_SCOPE_LEAK" for f in out["findings"])


def test_cursor_loop_fail_closed():
    t = _valid_transport()
    t.cursor_loop = True
    t.pages[DS] = [{"id": str(i), "project_id": "proj-lab"} for i in range(5)]
    out = run_preflight(t, _one_ds(), token="tok")
    assert out["status"] == "CURSOR_LOOP"
    assert out["verified"] is False


def test_missing_cursor_fail_closed():
    t = _valid_transport()
    t.missing_cursor = True
    t.pages[DS] = [{"id": str(i), "project_id": "proj-lab"} for i in range(5)]
    out = run_preflight(t, _one_ds(), token="tok")
    assert out["status"] == "MISSING_CURSOR"


def test_page_budget():
    proto = load_protocol()
    proto = deepcopy(proto)
    proto["max_pages"] = 1
    t = _valid_transport()
    t.pages[DS] = [{"id": str(i), "project_id": "proj-lab"} for i in range(10)]
    out = run_preflight(t, _one_ds(), token="tok", protocol=proto)
    assert out["status"] == "PAGE_BUDGET"


def test_relation_multi_page():
    t = _valid_transport()
    t.pages[DS] = [{"id": "a", "project_id": "proj-lab", "relation_page_id": "rel-1"}]
    t.relation_targets["rel-1"] = "expected-parent-hub"
    t.relation_pages["rel-1"] = [{"id": f"c{i}"} for i in range(5)]
    out = run_preflight(t, _one_ds(), token="tok")
    assert out["status"] == "PREFLIGHT_OK_FAKE_TRANSPORT"


def test_429_on_query_exhausted():
    t = _valid_transport()
    t.force_429 = 10
    t.force_429_path = "/query"
    t.retry_after = "1"
    clock = Clock()
    proto = deepcopy(load_protocol())
    proto["retry_budget"] = 2
    out = run_preflight(t, _one_ds(), token="tok", protocol=proto, clock=clock)
    assert out["status"] == "RATE_LIMITED"
    assert out.get("hop") == "query"


def test_401_on_relation_target():
    t = _valid_transport()
    t.pages[DS] = [{"id": "a", "project_id": "proj-lab", "relation_page_id": "rel-1"}]

    orig = t.request

    def wrapped(method, path, headers, params=None):
        if path.startswith("/v1/pages/rel-1") and not path.endswith("/relations"):
            t.auth_ok = False
        return orig(method, path, headers, params)

    t.request = wrapped
    out = run_preflight(t, _one_ds(), token="tok")
    assert out["status"] == "BLOCKED_ACCESS"
    assert out.get("hop") == "relation_target"


def test_malformed_schema_body():
    t = _valid_transport()
    t.malformed = True
    out = run_preflight(t, _one_ds(), token="tok")
    assert out["status"] == "MALFORMED_RESPONSE"


def test_no_token_zero_calls():
    t = _valid_transport()
    out = run_preflight(t, _one_ds(), token=None)
    assert out["status"] == "BLOCKED_ACCESS"
    assert t.calls == 0


def test_missing_protocol_blocked_owner():
    t = _valid_transport()
    out = run_preflight(t, _one_ds(), token="tok", protocol={})
    assert out["status"] == "BLOCKED_OWNER_INPUT"
