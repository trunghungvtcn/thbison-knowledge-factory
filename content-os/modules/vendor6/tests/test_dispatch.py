"""V6-R2-01: chain must call registry impls; Trap must fire; spies record hops."""

import pytest

from thbison_v6.adapters.registry import AdapterRegistry, HOPS, MissingAdapterError
from thbison_v6.adapters.spy import SpyAdapter
from thbison_v6.harness.lab import Lab, RegistryModeMismatch


class Trap:
    def __getattr__(self, name):
        raise RuntimeError("ACTUAL_ADAPTER_WAS_CALLED:" + name)


def test_trap_is_invoked_on_actual_chain(tmp_path):
    r = AdapterRegistry("ACTUAL_COMPONENTS")
    for hop in HOPS:
        r.bind(hop, "ACTUAL", Trap(), "probe")
    lab = Lab(mode="ACTUAL_COMPONENTS", root=tmp_path, registry=r)
    with pytest.raises(RuntimeError, match="ACTUAL_ADAPTER_WAS_CALLED:plan"):
        lab.run_reference_chain()


def test_spy_adapters_record_each_hop(tmp_path):
    base = Lab(mode="REFERENCE_ONLY", root=tmp_path / "base")
    spies = {}
    r = AdapterRegistry("ACTUAL_COMPONENTS")
    mapping = {
        "planning": base.planning,
        "knowledge": base.knowledge,
        "writer": base.writer,
        "runtime": base.runtime,
        "cms": base.cms,
    }
    for hop, inner in mapping.items():
        spies[hop] = SpyAdapter(inner, hop)
        r.bind(hop, "ACTUAL", spies[hop], "probe")
    lab = Lab(mode="ACTUAL_COMPONENTS", root=tmp_path / "act", registry=r)
    result = lab.run_chain()
    assert spies["planning"].calls and spies["planning"].calls[0]["method"] == "plan"
    assert any(c["method"] == "query" for c in spies["knowledge"].calls)
    methods_w = [c["method"] for c in spies["writer"].calls]
    assert "draft" in methods_w and "approve" in methods_w
    assert any(c["method"] == "publish" for c in spies["cms"].calls)
    assert any(c["method"] == "admit" for c in spies["runtime"].calls)
    kinds = {h["kind"] for h in result["trace"]}
    assert kinds == {"ACTUAL"}
    assert all(h["impl"] == "SpyAdapter" for h in result["trace"])
    assert all(h["verified_component"] is False for h in result["trace"])
    assert all(h["stub"] is False for h in result["trace"])


def test_one_hop_failure_does_not_fallback(tmp_path):
    base = Lab(mode="REFERENCE_ONLY", root=tmp_path / "b")

    class BoomKnowledge:
        kind = "ACTUAL"

        def query(self, brief):
            raise RuntimeError("KNOWLEDGE_DOWN")

    r = AdapterRegistry("MIXED", frozenset({"planning", "writer", "runtime", "cms"}))
    r.bind("planning", "STUB", base.planning, "VENDOR_1")
    r.bind("knowledge", "ACTUAL", BoomKnowledge(), "VENDOR_4")
    r.bind("writer", "STUB", base.writer, "VENDOR_2")
    r.bind("runtime", "STUB", base.runtime, "VENDOR_3")
    r.bind("cms", "STUB", base.cms, "VENDOR_5")
    lab = Lab(mode="MIXED", root=tmp_path / "m", registry=r, stub_hops=frozenset({"planning", "writer", "runtime", "cms"}))
    with pytest.raises(RuntimeError, match="KNOWLEDGE_DOWN"):
        lab.run_chain()
    # no cms effect from fallback
    assert lab.ledger.get_map("cms_by_receipt") == {}


def test_registry_mode_mismatch(tmp_path):
    r = AdapterRegistry("MIXED", frozenset({"planning"}))
    with pytest.raises(RegistryModeMismatch):
        Lab(mode="ACTUAL_COMPONENTS", root=tmp_path, registry=r)


def test_mixed_undeclared_stub_rejected(tmp_path):
    with pytest.raises(MissingAdapterError):
        Lab(mode="MIXED", root=tmp_path, stub_hops=frozenset({"planning"}))
