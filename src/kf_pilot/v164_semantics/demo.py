"""Synthetic fixtures only. Nothing here is a real engineering instruction."""
from __future__ import annotations

from pathlib import Path

from .canonical import canonical_bytes, digest, require, sha256
from .integration import Compatibility, Runtime
from .pipeline import ASSETS

TEXTS = (
    "TEST ONLY. Demo asset A has interval 1 year when indoors, except during quarantine.",
    "TEST ONLY. Demo asset B has interval 3 years when unused, except after an incident.",
    "TEST ONLY. For demo asset C, lifting people is prohibited.",
    "TEST ONLY. For demo asset D, overloading is prohibited.",
    "TEST ONLY. For demo asset E, side pulling is prohibited.",
    "TEST ONLY. Demo conditions: A; B. The connective is not established.",
)


def fixture_upstream_hash(candidate: dict) -> str:
    return digest({k: v for k, v in candidate.items() if k != "upstream_binding_hash"})


def fixture_runtime() -> Runtime:
    def upstream(candidate, issue):
        require(candidate["upstream_binding_hash"] == fixture_upstream_hash(candidate), "UPSTREAM_BINDING_HASH_MISMATCH")

    def compatible(issue, proposal):
        # DEMONSTRATION of the reported whole-literal restriction, NOT the real
        # V16.2 implementation. Production adapter MUST call the unchanged repo.
        value = proposal["target_semantic_payload"]["object_value"]
        exact_literal = value["kind"] == "quantity" and issue["source_text"] == f"{value['amount']} {value['unit']}"
        return Compatibility(exact_literal, "TEST_WHOLE_LITERAL_COMPATIBLE" if exact_literal else "V162_CONTRACT_INCOMPATIBLE")

    return Runtime("TEST_ONLY", "demo-identity/v164-preview", lambda entity, payload:
                   "demo_v164_" + digest({"entity_id": entity, "payload": payload}), upstream, compatible)


def fixture_assets(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    baseline = canonical_bytes({"TEST_ONLY": True, "label": "Synthetic baseline, not the V16.1 production plan"})
    (root / "baseline.json").write_bytes(baseline)
    raw = "\n".join(TEXTS).encode("utf-8")
    (root / "synthetic-source.txt").write_bytes(raw)
    raw_hash = sha256(raw)

    def span(text: str, part: str | None = None):
        full = raw.decode("utf-8")
        start = full.index(text) + (text.index(part) if part is not None else 0)
        quote = text if part is None else part
        return {"source_ref": "TEST-SOURCE", "raw_sha256": raw_hash, "extractor_id": "utf8/v1",
                "unit_id": "text:0", "start": start, "end": start + len(quote), "quote": quote}

    records, issues, candidates = [], [], []
    for i, text in enumerate(TEXTS):
        entity, version, issue_id = f"demo-entity-{i}", f"demo-base-{i}", f"demo-issue-{i}"
        predicate = "DEMO_INTERVAL" if i < 2 else "DEMO_PROHIBITION"
        condition = {"op": "UNRESOLVED", "raw_text": None} if i == 5 else {"op": "COMPARE", "field": "demo_mode", "comparator": "EQ", "value": f"case-{i}"}
        semantic = {"product_family": "TEST_ASSET", "subject": f"DEMO_ASSET_{i}",
                    "predicate": predicate, "object_value": {"legacy_text": text},
                    "applicability": {"scope": "TEST_REGION_ONLY", "asset": i},
                    "jurisdiction": "TEST_REGION", "legal_status": "NOT_A_REAL_RULE",
                    "condition_ast": condition,
                    "exception_ast": {"op": "COMPARE", "field": "demo_exception", "comparator": "EQ", "value": f"exception-{i}"}}
        records.append({"entity_id": entity, "version_id": version, "page_id": f"demo-page-{i}",
                        "parent_id": "demo-parent", "canonical_text": text, "system_status": "REVIEW_REQUIRED",
                        "decision": "PENDING", "reviewer_note": f"Preserve note {i}", "semantic_payload": semantic})
        field = "object_value" if i < 5 else "condition_ast"
        issues.append({"issue_id": issue_id, "issue_type": "OBJECT_VALUE_UNSTRUCTURED" if i < 5 else "CONDITION_CONNECTIVE_AMBIGUOUS",
                       "entity_id": entity, "version_id": version, "state": "NEEDS_REVIEW",
                       "before_value_hash": digest(semantic[field]), "source_text": text})
        if i == 5:
            continue
        interpretation = ({"kind": "quantity", "amount": "1" if i == 0 else "3", "unit": "year", "operator": "EQ"}
                          if i < 2 else {"kind": "enum", "code": f"PROHIBITION_{i}", "vocabulary_id": "demo-vocab"})
        proofs = ({"amount": span(text, "1" if i == 0 else "3"), "unit": span(text, "year" if i == 0 else "years")}
                  if i < 2 else {"statement": span(text, text.split(", ")[1][:-1])})
        candidate = {"candidate_id": f"demo-candidate-{i}", "issue_id": issue_id, "entity_id": entity,
                     "base_version_id": version, "predicate": predicate, "applicability": semantic["applicability"],
                     "proposer_id": "DEMO_MODEL", "context_span": span(text),
                     "interpretation": interpretation, "proofs": proofs}
        candidate["upstream_binding_hash"] = fixture_upstream_hash(candidate)
        candidates.append(candidate)
    return {
        "snapshot": {"schema": "v164-normalized/v1", "data_class": "TEST_ONLY", "as_of": "2026-09-05T00:00:00Z",
                     "baseline": {"path": "baseline.json", "sha256": sha256(baseline)},
                     "identity_contract_id": "demo-identity/v164-preview",
                     "sources": [{"source_ref": "TEST-SOURCE", "path": "synthetic-source.txt",
                                  "raw_sha256": raw_hash, "extractor_id": "utf8/v1"}],
                     "records": records, "issues": issues, "candidates": candidates},
        "predicate_contracts": {"data_class": "TEST_ONLY", "predicates": {
            "DEMO_INTERVAL": {"allowed_kinds": ["quantity"], "operators": ["EQ"],
                              "units": {"year": {"dimension": "time", "source_literals": ["year", "years"]}},
                              "vocabulary_ids": []},
            "DEMO_PROHIBITION": {"allowed_kinds": ["enum"], "operators": [], "units": {}, "vocabulary_ids": ["demo-vocab"]}}},
        "vocabularies": {"data_class": "TEST_ONLY", "entries": {}},
        "reviewer_registry": {"data_class": "TEST_ONLY", "entries": {}},
        "adjudications": {"data_class": "TEST_ONLY", "entries": []},
    }


def fixture_pins(assets: dict) -> dict:
    # For reproducible TEST fixtures only. Production must NOT generate its own
    # authority pins from unchecked inputs; see the independent trust-root contract.
    return {key: digest(assets[key]) for key in sorted(ASSETS)}


