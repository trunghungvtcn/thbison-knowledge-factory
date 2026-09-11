import json
from pathlib import Path

import pytest

from kf_pilot.v166_evidence_completion.canonical import ContractError, bytes_for, confined, digest, load, loads, sha256
from kf_pilot.v166_evidence_completion.acquisition import MAX_ATTEMPTS, MAX_REDIRECTS, MAX_SOURCE_BYTES, freeze, validate_public_url
from kf_pilot.v166_evidence_completion.pipeline import BASELINE, encode, offline_guard, project_shadow, write_new
from kf_pilot.v166_evidence_completion.verifier import verify
from kf_pilot.v166_evidence_completion.schemas import validate_ast, validate_research_plan, validate_run_config, validate_trust


@pytest.mark.parametrize("raw", ['{"a":1,"a":2}', '{"x":{},"x":[]}'])
def test_duplicate_json_keys(raw):
    with pytest.raises(ContractError, match="DUPLICATE_JSON_KEY"):
        loads(raw)


@pytest.mark.parametrize("value", ["../x", "a/../../x", "..\\x"])
def test_path_traversal(tmp_path, value):
    with pytest.raises(ContractError, match="PATH_TRAVERSAL"):
        confined(tmp_path, value)


@pytest.mark.parametrize("value", ["/x", r"C:\\x", "C:x", r"\\\\server\\share\\x"])
def test_absolute_path_rejected_on_every_runner(tmp_path, value):
    with pytest.raises(ContractError, match="ABSOLUTE_PATH"):
        confined(tmp_path, value)


def test_freeze_confines_source_and_preserves_same_basename_inputs(tmp_path):
    acquired = tmp_path / "acquired"
    (acquired / "a").mkdir(parents=True)
    (acquired / "b").mkdir()
    (acquired / "a" / "same.txt").write_bytes(b"A")
    (acquired / "b" / "same.txt").write_bytes(b"B")
    rows = [
        {"status": "FETCHED", "local_path": "a/same.txt", "sha256": sha256(b"A")},
        {"status": "FETCHED", "local_path": "b/same.txt", "sha256": sha256(b"B")},
    ]
    (acquired / "acquisition_manifest.json").write_bytes(bytes_for({"sources": rows}))
    (acquired / "discovery_log.jsonl").write_bytes(b"")
    output = tmp_path / "frozen"
    freeze(acquired, "2026-09-10T00:00:00Z", output)
    manifest = load(output / "frozen_corpus_manifest.json")
    paths = [output / row["local_path"] for row in manifest["sources"]]
    assert len({path.name for path in paths}) == 2
    assert [path.read_bytes() for path in paths] == [b"A", b"B"]


def test_freeze_rejects_outside_source_root_before_read(tmp_path):
    acquired = tmp_path / "acquired"
    acquired.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"outside")
    row = {"status": "FETCHED", "local_path": "../outside.txt", "sha256": sha256(b"outside")}
    (acquired / "acquisition_manifest.json").write_bytes(bytes_for({"sources": [row]}))
    (acquired / "discovery_log.jsonl").write_bytes(b"")
    output = tmp_path / "frozen"
    with pytest.raises(ContractError, match="PATH_TRAVERSAL"):
        freeze(acquired, "2026-09-10T00:00:00Z", output)
    assert not output.exists()
    assert not list(tmp_path.glob("frozen.staging-*"))


@pytest.mark.parametrize("op", ["AND", "OR"])
def test_ast_branches(op):
    leaf = {"op": "PREDICATE", "field": "fixed", "cmp": "EQ", "value": True}
    assert validate_ast({"op": op, "args": [leaf, leaf]})["op"] == op


@pytest.mark.parametrize("cmp", ["EQ", "NE", "GT", "GTE", "LT", "LTE", "IN"])
def test_ast_comparators(cmp):
    assert validate_ast({"op": "PREDICATE", "field": "age", "cmp": cmp, "value": 12})


def test_ast_unresolved_allowed():
    assert validate_ast({"op": "UNRESOLVED", "reason": "connective unknown"})


def test_ast_unknown_rejected():
    with pytest.raises(ContractError, match="AST_UNKNOWN_OPERATOR"):
        validate_ast({"op": "EXEC", "args": []})


def test_ast_depth_bound():
    node = {"op": "UNRESOLVED", "reason": "x"}
    for _ in range(14):
        node = {"op": "NOT", "arg": node}
    with pytest.raises(ContractError, match="AST_DEPTH_LIMIT"):
        validate_ast(node)


@pytest.mark.parametrize("bad", ["http://example.com/x", "file:///x", "ftp://example.com/x"])
def test_research_plan_https_only(bad):
    plan = {"schema_version": 1, "sources": [{"source_id": "x", "url": bad, "role": "r", "provenance_family": "p"}]}
    with pytest.raises(ContractError, match="PUBLIC_HTTPS_REQUIRED"):
        validate_research_plan(plan)


def test_duplicate_source_id():
    item = {"source_id": "x", "url": "https://example.com/x", "role": "r", "provenance_family": "p"}
    with pytest.raises(ContractError, match="DUPLICATE_SOURCE_ID"):
        validate_research_plan({"schema_version": 1, "sources": [item, item]})


@pytest.mark.parametrize("url", ["https://127.0.0.1/x", "https://[::1]/x", "https://localhost/x"])
def test_public_fetch_rejects_loopback(url):
    with pytest.raises((ContractError, RuntimeError), match="NON_PUBLIC_FETCH_TARGET|DNS_RESOLUTION_FAILED"):
        validate_public_url(url)


def test_acquisition_bounds_are_explicit():
    assert MAX_SOURCE_BYTES == 20 * 1024 * 1024
    assert MAX_REDIRECTS == 5
    assert MAX_ATTEMPTS == 2


@pytest.mark.parametrize("extra", [{"extra": 1}, {"schema_version": 2}])
def test_run_config_strict(extra):
    value = {"schema_version": 1, "data_class": "REPOSITORY", "as_of": "2026-09-05T00:00:00Z", "frozen_corpus": "x", "v165_run": "y", "expected_baseline": "z", "target_entity_ids": []}
    value.update(extra)
    with pytest.raises(ContractError):
        validate_run_config(value)


def test_duplicate_targets():
    value = {"schema_version": 1, "data_class": "REPOSITORY", "as_of": "2026-09-05T00:00:00Z", "frozen_corpus": "x", "v165_run": "y", "expected_baseline": "z", "target_entity_ids": ["x", "x"]}
    with pytest.raises(ContractError, match="DUPLICATE_TARGET"):
        validate_run_config(value)


@pytest.mark.parametrize("missing", ["registry", "activation", "adjudication"])
def test_trust_roots_complete(missing):
    pins = {"registry": "x", "activation": "y", "adjudication": "z"}; pins.pop(missing)
    with pytest.raises(ContractError):
        validate_trust({"schema_version": 1, "trusted_pins": pins, "receipts": dict(pins)})


@pytest.mark.parametrize("value", [{}, [], "x", 1, None, True])
def test_canonical_determinism(value):
    assert sha256(bytes_for(value)) == digest(value)


def test_jsonl_encoding():
    raw = encode("x.jsonl", [{"b": 2, "a": 1}])
    assert raw == b'{"a":1,"b":2}\n'


def test_offline_guard_blocks_socket():
    import socket
    with offline_guard() as attempts:
        with pytest.raises(RuntimeError, match="FORBIDDEN_TRANSPORT"):
            socket.socket().connect(("127.0.0.1", 9))
    assert attempts["network"] == 1


def test_handoff_baseline_constant():
    from kf_pilot.v166_evidence_completion.pipeline import BASELINE
    assert BASELINE == "af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399"


def test_synthetic_accept_project_and_independent_verify(tmp_path):
    config = {"schema_version": 1, "data_class": "TEST_ONLY", "as_of": "2026-09-05T00:00:00Z",
              "frozen_corpus": "x", "v165_run": "y", "expected_baseline": BASELINE, "target_entity_ids": ["e1"]}
    config_path = tmp_path / "config.json"; config_path.write_bytes(bytes_for(config) + b"\n")
    proposal = {"schema_version": 1, "data_class": "TEST_ONLY", "entity_id": "e1", "base_version_id": "v1",
                "target_version_id": "v2", "state": "COMPLETE_PENDING_REVIEW", "corpus_revision": "c", "as_of": config["as_of"],
                "original_issue_ids": ["i0"], "evidence_span_ids": ["s1"],
                "gap_assessment": {"conditions": "SUPPORTED", "exceptions": "SUPPORTED", "overlap": "SUPPORTED", "legal_time": "SUPPORTED"},
                "after_semantic_payload": {"predicate": "inspection_interval"}, "actual_field_diff": ["condition_ast"],
                "current_record": {"page_id": "p1", "parent_id": "staging", "version_id": "v1", "semantic_payload": {}, "decision": "APPROVED", "reviewer_note": "keep"},
                "dependency_records": [], "authorized_to_execute": False}
    proposal["proposal_hash"] = digest(proposal)
    issues = [{"issue_id": f"i{x}", "entity_id": "e1" if x == 0 else f"other{x}", "resolution_status": "NEEDS_REVIEW"} for x in range(85)]
    proposal_dir = tmp_path / "proposal"
    write_new(proposal_dir, {"interpretation_candidates.jsonl": [proposal], "expanded_issue_ledger.json": {"issues": issues}})
    registry = {"issuer": "external"}
    activation = {"decision": "APPROVE_LOCAL_SHADOW", "target_entity_ids": ["e1"]}
    adjudication = {"decision": "ACCEPT", "proposal_hash": proposal["proposal_hash"], "base_version_id": "v1", "target_version_id": "v2"}
    trust = {"schema_version": 1, "trusted_pins": {"registry": digest(registry), "activation": digest(activation), "adjudication": digest(adjudication)},
             "receipts": {"registry": registry, "activation": activation, "adjudication": adjudication}}
    trust_path = tmp_path / "trust.json"; trust_path.write_bytes(bytes_for(trust) + b"\n")
    committed = tmp_path / "committed"
    result = project_shadow(config_path, proposal_dir, trust_path, committed)
    assert result["apply"] == "LOCAL_SHADOW_PROJECTED"
    checked = verify(config_path, committed, tmp_path / "verify.json")
    assert checked["status"] == "V166_INDEPENDENT_VERIFY_PASS"
