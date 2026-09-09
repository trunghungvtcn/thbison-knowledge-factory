from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .canonical import (GateError, canonical_bytes, confined_path, digest, exact_keys,
                        nonempty, require, sha256, unique_index)
from .evidence import Extractor, SourceStore
from .integration import Runtime
from .interpretation import interpret
from .review import validate_adjudication

ASSETS = frozenset({"snapshot", "predicate_contracts", "vocabularies",
                   "reviewer_registry", "adjudications"})
SEMANTIC_FIELDS = frozenset({"product_family", "subject", "predicate", "object_value",
                            "applicability", "jurisdiction", "legal_status",
                            "condition_ast", "exception_ast"})


def validate_assets(assets: dict, expected_hashes: dict, runtime: Runtime) -> dict:
    require(set(assets) == ASSETS and set(expected_hashes) == ASSETS, "TRUST_ROOTS_INCOMPLETE")
    for name in sorted(ASSETS):
        require(digest(assets[name]) == expected_hashes[name], "INPUT_PIN_MISMATCH", name)
        require(assets[name].get("data_class") == runtime.data_class, "TEST_DATA_CLASS_MISMATCH", name)
    require(runtime.data_class in {"TEST_ONLY", "REPOSITORY"}, "INVALID_DATA_CLASS")
    snapshot = assets["snapshot"]
    exact_keys(snapshot, {"schema", "data_class", "as_of", "baseline", "identity_contract_id",
                          "sources", "records", "issues", "candidates"})
    require(snapshot["schema"] == "v164-normalized/v1", "SNAPSHOT_SCHEMA_MISMATCH")
    require(snapshot["identity_contract_id"] == runtime.identity_contract_id,
            "IDENTITY_CONTRACT_MISMATCH")
    exact_keys(assets["predicate_contracts"], {"data_class", "predicates"})
    for predicate in assets["predicate_contracts"]["predicates"].values():
        exact_keys(predicate, {"allowed_kinds", "operators", "units", "vocabulary_ids"})
    exact_keys(assets["vocabularies"], {"data_class", "entries"})
    for vocab in assets["vocabularies"]["entries"].values():
        exact_keys(vocab, {"authority_ref", "version", "entries"})
        require(nonempty(vocab["authority_ref"]) and nonempty(vocab["version"]), "VOCAB_AUTHORITY_MISSING")
        for entry in vocab["entries"].values():
            exact_keys(entry, {"definition", "source_literals"})
            require(nonempty(entry["definition"]) and bool(entry["source_literals"]), "VOCAB_ENTRY_INVALID")
    exact_keys(assets["reviewer_registry"], {"data_class", "entries"})
    exact_keys(assets["adjudications"], {"data_class", "entries"})
    return snapshot


def validate_records(snapshot: dict) -> tuple[dict, dict]:
    records = unique_index(snapshot["records"], "entity_id")
    pages = set()
    for record in records.values():
        exact_keys(record, {"entity_id", "version_id", "page_id", "parent_id", "canonical_text",
                            "system_status", "decision", "reviewer_note", "semantic_payload"})
        for key in ("version_id", "page_id", "parent_id", "canonical_text"):
            require(nonempty(record[key]), "RECORD_FIELD_MISSING", key)
        require(record["page_id"] not in pages, "MAPPING_COLLISION")
        pages.add(record["page_id"])
        require(record["system_status"] in {"REVIEW_REQUIRED", "HOLD", "REJECTED"}, "UNKNOWN_SYSTEM_STATUS")
        require(record["decision"] in {"PENDING", "APPROVED", "HOLD", "REJECTED"}, "UNKNOWN_HUMAN_DECISION")
        exact_keys(record["semantic_payload"], SEMANTIC_FIELDS)
        for field in ("product_family", "subject", "predicate"):
            require(nonempty(record["semantic_payload"][field]), "SEMANTIC_FIELD_MISSING", field)
        require(record["semantic_payload"]["applicability"] is not None, "APPLICABILITY_REQUIRED")
    issues = unique_index(snapshot["issues"], "issue_id")
    seen = set()
    for issue in issues.values():
        exact_keys(issue, {"issue_id", "issue_type", "entity_id", "version_id", "state",
                           "before_value_hash", "source_text"})
        require(issue["issue_type"] in {"OBJECT_VALUE_UNSTRUCTURED", "CONDITION_CONNECTIVE_AMBIGUOUS"},
                "UNKNOWN_ISSUE_TYPE")
        require(issue["state"] in {"HOLD", "NEEDS_REVIEW"}, "UNRESOLVED_LEDGER_REQUIRED")
        require(issue["entity_id"] in records, "ISSUE_ENTITY_MISMATCH")
        record = records[issue["entity_id"]]
        require(issue["version_id"] == record["version_id"], "ISSUE_VERSION_MISMATCH")
        key = (issue["entity_id"], issue["version_id"], issue["issue_type"])
        require(key not in seen, "DUPLICATE_ISSUE_IDENTITY")
        seen.add(key)
        field = "object_value" if issue["issue_type"] == "OBJECT_VALUE_UNSTRUCTURED" else "condition_ast"
        before_value = record["semantic_payload"][field]
        # The repository V16.2 ledger intentionally hashes the legacy scalar,
        # while the semantic payload wraps it as {type: legacy_text, value: ...}.
        # Normalize that explicit representation without weakening drift checks.
        if (issue["issue_type"] == "OBJECT_VALUE_UNSTRUCTURED" and
                isinstance(before_value, dict) and before_value.get("type") == "legacy_text" and
                set(before_value) == {"type", "value"}):
            before_value = before_value["value"]
        require(digest(before_value) == issue["before_value_hash"], "ISSUE_BEFORE_HASH_MISMATCH")
    return records, issues


def make_proposal(candidate: dict, issue: dict, record: dict, assets: dict,
                  store: SourceStore, runtime: Runtime) -> dict:
    exact_keys(candidate, {"candidate_id", "upstream_binding_hash", "issue_id", "entity_id",
                           "base_version_id", "predicate", "applicability", "proposer_id",
                           "context_span", "interpretation", "proofs"})
    require(candidate["entity_id"] == issue["entity_id"], "CANDIDATE_ENTITY_MISMATCH")
    require(candidate["base_version_id"] == issue["version_id"], "CANDIDATE_VERSION_MISMATCH")
    require(candidate["issue_id"] == issue["issue_id"], "CANDIDATE_ISSUE_MISMATCH")
    require(nonempty(candidate["proposer_id"]), "PROPOSER_REQUIRED")
    require(candidate["predicate"] == record["semantic_payload"]["predicate"], "PREDICATE_MISMATCH")
    require(candidate["applicability"] == record["semantic_payload"]["applicability"], "APPLICABILITY_MISMATCH")
    runtime.verify_upstream(candidate, issue)
    typed_value = interpret(candidate, issue, store, assets["predicate_contracts"]["predicates"],
                            assets["vocabularies"]["entries"])
    semantic = deepcopy(record["semantic_payload"])
    semantic["object_value"] = typed_value
    require(digest(semantic) != digest(record["semantic_payload"]), "NO_SEMANTIC_CHANGE")
    target_version = runtime.version_id(record["entity_id"], semantic)
    require(nonempty(target_version) and target_version != record["version_id"], "INVALID_TARGET_VERSION")
    proposal = {
        "contract": "evidence_derived_value/v1", "data_class": runtime.data_class,
        "candidate_id": candidate["candidate_id"], "issue_id": issue["issue_id"],
        "entity_id": record["entity_id"], "base_version_id": record["version_id"],
        "target_version_id": target_version, "identity_contract_id": runtime.identity_contract_id,
        "page_id": record["page_id"], "parent_id": record["parent_id"],
        "predicate": candidate["predicate"], "proposer_id": candidate["proposer_id"],
        "semantic_hash": digest(semantic), "target_semantic_payload": semantic,
        "base_record_hash": digest(record), "before_value_hash": issue["before_value_hash"],
        "after_value_hash": digest(typed_value), "source_text": issue["source_text"],
        "canonical_text": record["canonical_text"], "context_span": deepcopy(candidate["context_span"]),
        "proofs": deepcopy(candidate["proofs"]), "upstream_binding_hash": candidate["upstream_binding_hash"],
        "candidate_hash": digest(candidate),
        "predicate_contract_hash": digest(assets["predicate_contracts"]),
        "vocabulary_contract_hash": digest(assets["vocabularies"]),
    }
    proposal["proposal_hash"] = digest(proposal)
    return proposal


def run(assets: dict, expected_hashes: dict, *, root: Path, runtime: Runtime,
        extractors: dict[str, Extractor]) -> dict[str, object]:
    """Pure local analysis. All outputs are returned; this function writes nothing.

    Trust pins must be obtained independently of candidate content. A hash proves
    byte identity, not that a person or authority approved an artifact.
    """
    original = canonical_bytes(assets)
    snapshot = validate_assets(assets, expected_hashes, runtime)
    exact_keys(snapshot["baseline"], {"path", "sha256"})
    baseline = confined_path(root, snapshot["baseline"]["path"])
    require(sha256(baseline.read_bytes()) == snapshot["baseline"]["sha256"], "V161_BASELINE_MISMATCH")
    records, issues = validate_records(snapshot)
    store = SourceStore(root, snapshot["sources"], extractors)
    candidates = unique_index(snapshot["candidates"], "candidate_id")
    proposals, diagnostics = [], []
    for candidate_id, candidate in sorted(candidates.items()):
        require(candidate.get("issue_id") in issues, "ORPHAN_CANDIDATE", candidate_id)
        issue = issues[candidate["issue_id"]]
        try:
            proposal = make_proposal(candidate, issue, records[issue["entity_id"]], assets, store, runtime)
            preview = runtime.check_v162(issue, proposal)
            require(type(preview.compatible) is bool and nonempty(preview.reason), "INVALID_COMPATIBILITY_RESULT")
            proposals.append(proposal)
            diagnostics.append({"candidate_id": candidate_id, "issue_id": issue["issue_id"],
                                "status": "AWAITING_ADJUDICATION", "reason": None,
                                "proposal_hash": proposal["proposal_hash"],
                                "compatibility_preview": {"compatible": preview.compatible, "reason": preview.reason}})
        except GateError as error:
            diagnostics.append({"candidate_id": candidate_id, "issue_id": issue["issue_id"],
                                "status": "BLOCKED", "reason": error.code, "proposal_hash": None,
                                "compatibility_preview": {"compatible": False, "reason": "PROPOSAL_BLOCKED"}})
    proposal_by_hash = {p["proposal_hash"]: p for p in proposals}
    adjudications = unique_index(assets["adjudications"]["entries"], "proposal_hash")
    for key in adjudications:
        require(key in proposal_by_hash, "ORPHAN_OR_STALE_ADJUDICATION", key)
    accepted, adapter_inputs, review_results = [], [], []
    accepted_entities = set()
    for proposal in proposals:
        review = adjudications.get(proposal["proposal_hash"])
        if review is None:
            continue
        decision = validate_adjudication(review, proposal, assets["reviewer_registry"]["entries"],
                                         data_class=runtime.data_class, as_of=snapshot["as_of"])
        result = {"issue_id": proposal["issue_id"], "proposal_hash": proposal["proposal_hash"],
                  "decision": decision, "adapter_status": "NOT_APPLICABLE"}
        if decision == "ACCEPT":
            entity_id = proposal["entity_id"]
            require(entity_id not in accepted_entities, "MULTIPLE_ACCEPTS_PER_ENTITY")
            accepted_entities.add(entity_id)
            accepted.append({"proposal": proposal, "adjudication": deepcopy(review)})
            record = records[entity_id]
            issue = issues[proposal["issue_id"]]
            if issue["state"] == "HOLD" or record["system_status"] in {"HOLD", "REJECTED"} or record["decision"] in {"HOLD", "REJECTED"}:
                result["adapter_status"] = "BLOCKED_EXISTING_HOLD_OR_REJECTION"
            else:
                compatibility = runtime.check_v162(issue, proposal)
                require(type(compatibility.compatible) is bool and nonempty(compatibility.reason), "INVALID_COMPATIBILITY_RESULT")
                result["adapter_status"] = "V162_INPUT_READY" if compatibility.compatible else compatibility.reason
                if compatibility.compatible:
                    adapter_inputs.append({"data_class": runtime.data_class, "proposal_hash": proposal["proposal_hash"],
                                           "issue_id": issue["issue_id"], "entity_id": entity_id,
                                           "base_version_id": record["version_id"], "target_version_id": proposal["target_version_id"],
                                           "source_text": issue["source_text"], "before_value_hash": issue["before_value_hash"],
                                           "typed_value": proposal["target_semantic_payload"]["object_value"],
                                           "adjudication": deepcopy(review)})
        review_results.append(result)
    work_items = []
    for issue_id, issue in sorted(issues.items()):
        related = [d for d in diagnostics if d["issue_id"] == issue_id]
        reviews = [r for r in review_results if r["issue_id"] == issue_id]
        work_items.append({"issue_id": issue_id, "entity_id": issue["entity_id"], "version_id": issue["version_id"],
                           "issue_type": issue["issue_type"], "upstream_state": issue["state"],
                           "candidate_diagnostics": related, "review_results": reviews,
                           "resolution_status": "UPSTREAM_RECONCILIATION_REQUIRED" if any(r["adapter_status"] == "V162_INPUT_READY" for r in reviews)
                           else ("HOLD" if issue["state"] == "HOLD" else "NEEDS_REVIEW")})
    require(len(work_items) == len(issues), "ISSUE_ACCOUNTING_MISMATCH")
    require(original == canonical_bytes(assets), "INPUT_MUTATION_DETECTED")
    require(sha256(baseline.read_bytes()) == snapshot["baseline"]["sha256"], "V161_BASELINE_CHANGED")
    report = {
        "status": "V164_REFERENCE_PIPELINE_PASS", "data_class": runtime.data_class, "mode": "NO_WRITE",
        "baseline_before": snapshot["baseline"]["sha256"], "baseline_after": sha256(baseline.read_bytes()),
        "records": len(records), "issues": len(issues), "candidates": len(candidates),
        "valid_proposals": len(proposals), "blocked_candidates": len(candidates) - len(proposals),
        "adjudications": len(adjudications), "accepted_derivations": len(accepted),
        "compatible_adapter_inputs": len(adapter_inputs), "resolved_by_this_run": 0,
        "upstream_unresolved": len(issues), "post_v162_reconciliation": "NOT_EXECUTED_BY_THIS_PACK",
        "eligible_production_records": 0, "eligible_canary_records": 0,
        "production_writes": 0, "human_field_writes": 0, "create_operations": 0,
        "sql_executions": 0, "schema_mutations": 0, "scheduler_actions": 0,
        "authorized_to_execute": False, "repository_acceptance": "NOT_ESTABLISHED_BY_REFERENCE_RUN",
    }
    return {
        "v164_candidate_diagnostics.jsonl": diagnostics,
        "v164_semantic_proposals.jsonl": proposals,
        "v164_review_results.jsonl": review_results,
        "v164_accepted_derivations.jsonl": accepted,
        "v164_adapter_inputs.jsonl": adapter_inputs,
        "v164_issue_accounting.jsonl": work_items,
        "v164_mapping_snapshot.jsonl": [{k: records[e][k] for k in ("entity_id", "version_id", "page_id", "parent_id")} for e in sorted(records)],
        "v164_human_audit_snapshot.jsonl": [{k: records[e][k] for k in ("entity_id", "decision", "reviewer_note", "system_status")} for e in sorted(records)],
        "v164_input_manifest.json": {"schema": "v164-manifest/v1", "data_class": runtime.data_class,
                                     "input_hashes": deepcopy(expected_hashes), "identity_contract_id": runtime.identity_contract_id},
        "v164_contract_gap_report.json": {
            "data_class": runtime.data_class, "old_gate_modified": False,
            "diagnostics": diagnostics,
            "action": "Keep incompatible derivations in the sidecar; any new repository extension needs its own reviewed contract and unchanged legacy regression tests.",
        },
        "v164_post_v162_reconciliation.json": {
            "status": "NOT_EXECUTED", "reason": "REFERENCE_PACKAGE_HAS_NO_EXECUTED_V162_REPOSITORY",
            "upstream_issue_ids": sorted(issues), "resolved_delta": 0,
            "input_manifest": "v164_input_manifest.json",
        },
        "v164_readiness_report.json": report,
        "v164_phase_f_canary_plan.json": {"records": [], "authorized_to_execute": False,
                                         "reason": "EXISTING_REPOSITORY_GATES_AND_PHASE_F_REQUIRED"},
    }

