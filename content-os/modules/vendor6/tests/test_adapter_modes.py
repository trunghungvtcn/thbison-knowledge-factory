import pytest
from thbison_v6.adapters.http_client import FakeHttpTransport, HttpJsonClient
from thbison_v6.adapters.hops import KnowledgeHttpAdapter
from thbison_v6.adapters.process import ProcessLauncher
from thbison_v6.adapters.registry import AdapterRegistry, MissingAdapterError
from thbison_v6.contract_validate import assert_valid
from thbison_v6.harness.lab import Lab
from thbison_v6.hashutil import evidence_snapshot_sha256


def test_actual_mode_fails_without_adapters(tmp_path):
    with pytest.raises(MissingAdapterError, match="MISSING_ADAPTER:planning"):
        Lab(mode="ACTUAL_COMPONENTS", root=tmp_path)


def test_mixed_requires_declared_stubs_only(tmp_path):
    with pytest.raises(MissingAdapterError):
        Lab(mode="MIXED", root=tmp_path, stub_hops=frozenset({"planning"}))


def test_mixed_ok_when_actual_hops_bound(tmp_path):
    lab = Lab(mode="REFERENCE_ONLY", root=tmp_path)
    reg = AdapterRegistry("MIXED", frozenset({"planning", "writer", "runtime", "cms"}))
    transport = FakeHttpTransport()

    def handler(headers, body):
        # return a valid bundle
        from thbison_v6.harness.lab import Lab as L

        b = L().knowledge.query(
            {
                "project_id": body["project_id"],
                "product_refs": [body["product_id"]],
                "scope": {"country_code": body["jurisdiction"], "language": "vi", "timezone": "Asia/Bangkok", "domain": "x"},
            }
        )
        return 200, b

    transport.route("POST", "/v1/knowledge/query", handler)
    client = HttpJsonClient("http://vendor4.example", transport, token="lab")
    adapter = KnowledgeHttpAdapter(client)
    reg.bind("planning", "STUB", lab.planning, "VENDOR_1")
    reg.bind("knowledge", "ACTUAL", adapter, "VENDOR_4", "http://vendor4.example")
    reg.bind("writer", "STUB", lab.writer, "VENDOR_2")
    reg.bind("runtime", "STUB", lab.runtime, "VENDOR_3")
    reg.bind("cms", "STUB", lab.cms, "VENDOR_5")
    lab2 = Lab(mode="MIXED", root=tmp_path / "m", registry=reg, stub_hops=frozenset({"planning", "writer", "runtime", "cms"}))
    assert lab2.hop_kind("knowledge") == "ACTUAL"
    assert lab2.hop_kind("planning") == "STUB"
    bundle = adapter.query(lab.planning.plan({"project_id": "proj-lab"})["brief"])
    assert_valid("EvidenceBundle", bundle)
    assert transport.calls and transport.calls[0].headers.get("Authorization", "").startswith("Bearer")
    # proposed mapping present in request body
    assert transport.calls[0].body["mapping"] == "PROPOSED_V6_CONTENTBRIEF_TO_V4_QUERY"


def test_process_launcher_requires_pinned_command():
    with pytest.raises(RuntimeError, match="MISSING_START_COMMAND"):
        ProcessLauncher(None).start()


def test_http_401_on_actual_knowledge():
    t = FakeHttpTransport()
    t.route("POST", "/v1/knowledge/query", lambda h, b: (401, {"code": "UNAUTHORIZED"}))
    adapter = KnowledgeHttpAdapter(HttpJsonClient("http://v4", t, token="x"))
    with pytest.raises(RuntimeError, match="KNOWLEDGE_HTTP_401"):
        adapter.query(
            {
                "project_id": "proj-lab",
                "product_refs": ["THB-PILOT"],
                "scope": {"country_code": "VN", "language": "vi"},
            }
        )
