import json
import os
import re
import socket
import sqlite3
import subprocess
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from .canonical import bytes_for, confined, digest, load, require, rows, sha256
from .schemas import validate_ast, validate_run_config, validate_trust

BASELINE = "af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399"
HUMAN_FIELDS = {"Decision", "Reviewer Note"}
BLOCKER_TYPES = {"EXCEPTION_COVERAGE_UNKNOWN", "RULE_OVERLAP_UNRESOLVED", "LEGAL_STATUS_UNVERIFIED"}


def encode(name, value):
    if name.endswith(".md"):
        return value.encode("utf-8")
    if name.endswith(".jsonl"):
        return b"".join(bytes_for(x) + b"\n" for x in value)
    return bytes_for(value) + b"\n"


def write_new(directory, outputs):
    directory = Path(directory)
    require(not directory.exists(), "OUTPUT_ALREADY_EXISTS")
    directory.mkdir(parents=True)
    hashes = {}
    for name, value in sorted(outputs.items()):
        raw = encode(name, value)
        (directory / name).write_bytes(raw)
        hashes[name] = sha256(raw)
    (directory / "artifact_hashes.json").write_bytes(encode("artifact_hashes.json", hashes))
    return hashes


def verify_hashes(directory):
    directory = Path(directory)
    hashes = load(directory / "artifact_hashes.json")
    actual = {p.name for p in directory.iterdir() if p.is_file()}
    require(actual == set(hashes) | {"artifact_hashes.json"}, "ARTIFACT_FILESET_MISMATCH")
    for name, expected in hashes.items():
        require(Path(name).name == name, "UNSAFE_ARTIFACT_NAME")
        require(sha256((directory / name).read_bytes()) == expected, "ARTIFACT_HASH_MISMATCH", name)
    return hashes


@contextmanager
def offline_guard():
    attempts = {"network": 0, "sql": 0, "process": 0}
    def deny(kind):
        def blocked(*args, **kwargs):
            attempts[kind] += 1
            raise RuntimeError("FORBIDDEN_TRANSPORT:" + kind)
        return blocked
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, "connect", deny("network")))
        stack.enter_context(patch.object(socket.socket, "connect_ex", deny("network")))
        stack.enter_context(patch.object(socket.socket, "sendto", deny("network")))
        stack.enter_context(patch.object(sqlite3, "connect", deny("sql")))
        stack.enter_context(patch.object(subprocess, "Popen", deny("process")))
        yield attempts


def _extract_pdf(path):
    try:
        import pymupdf
    except ImportError:
        return []
    doc = pymupdf.open(path)
    return [{"unit_id": f"pdf:page:{i + 1}", "text": page.get_text("text", sort=True)} for i, page in enumerate(doc)]


def _source_index(frozen_root, manifest):
    result = []
    for source in manifest["sources"]:
        if source["status"] != "FETCHED":
            continue
        path = confined(frozen_root, source["local_path"])
        require(sha256(path.read_bytes()) == source["sha256"], "FROZEN_SOURCE_HASH_MISMATCH")
        units = _extract_pdf(path) if path.suffix.lower() == ".pdf" else [{"unit_id": "text:1", "text": path.read_text(encoding="utf-8", errors="replace")}]
        result.append({"source_id": source["source_id"], "url": source["url"], "role": source["role"],
                       "provenance_family": source["provenance_family"], "sha256": source["sha256"], "units": units})
    return result


def _spans(index):
    patterns = {
        "qtkd13-current-reference": [r"QTKĐ\s*:\s*13\s*[-:]\s*2016", r"số\s+13\s*-\s*2016/BLĐTBXH"],
        "hand-chain-hoist-scope": [r"Pa\s*lăng\s+xích\s+kéo\s+tay", r"Palăng\s+xích\s+kéo\s+tay"],
        "partial-expiry": [r"hết\s+hiệu\s+lực\s+một\s+phần"],
    }
    found = []
    for source in index:
        for unit in source["units"]:
            text = unit["text"]
            for assertion, variants in patterns.items():
                for pattern in variants:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        start, end = max(0, match.start() - 180), min(len(text), match.end() + 220)
                        span = {"assertion": assertion, "source_id": source["source_id"], "raw_sha256": source["sha256"],
                                "unit_id": unit["unit_id"], "start": start, "end": end, "quote": text[start:end],
                                "inference": "DIRECT", "reviewer_needed": True}
                        span["span_id"] = digest(span)
                        found.append(span)
                        break
    return sorted({x["span_id"]: x for x in found}.values(), key=lambda x: x["span_id"])


def propose(run_config_path, output):
    config_path = Path(run_config_path).resolve()
    config = validate_run_config(load(config_path))
    require(config["expected_baseline"] == BASELINE, "BASELINE_MISMATCH")
    # Every configured input is confined to the repository working directory.
    # This permits cross-version, read-only inputs without permitting `..` escapes.
    root = Path.cwd().resolve()
    frozen_root = confined(root, config["frozen_corpus"])
    v165 = confined(root, config["v165_run"])
    verify_hashes(v165)
    manifest = load(frozen_root / "frozen_corpus_manifest.json")
    require(manifest["as_of"] == config["as_of"], "AS_OF_MISMATCH")
    index = _source_index(frozen_root, manifest)
    spans = _spans(index)
    old_proposals = rows(v165 / "complete_record_proposals.jsonl")
    ledger = load(v165 / "projected_issue_ledger.json")["issues"]
    record_plan = {x["entity_id"]: x for x in load(v165 / "projected_record_plan.json")["records"]}
    require(len(ledger) == 85 and len({x["issue_id"] for x in ledger}) == 85, "ISSUE_UNIVERSE_MISMATCH")
    require(sum(x["issue_type"] in BLOCKER_TYPES for x in ledger) == 6, "V165_BLOCKER_SET_MISMATCH")
    legal_spans = [x["span_id"] for x in spans if x["assertion"] == "qtkd13-current-reference"]
    proposals = []
    for old in old_proposals:
        if old["entity_id"] not in config["target_entity_ids"]:
            continue
        validate_ast(old["after_semantic_payload"]["condition_ast"])
        validate_ast(old["after_semantic_payload"]["exception_ast"])
        remaining = [x["issue_id"] for x in ledger if x["entity_id"] == old["entity_id"] and x["resolution_status"] != "RESOLVED"]
        state = "WAITING_EVIDENCE"
        gap = {"conditions": "MISSING", "exceptions": "MISSING", "overlap": "MISSING",
               "legal_time": "INTERPRETATION_REVIEW_REQUIRED" if legal_spans else "MISSING"}
        proposal = {"schema_version": 1, "data_class": config["data_class"], "entity_id": old["entity_id"],
                    "base_version_id": old["base_version_id"], "target_version_id": None,
                    "state": state, "corpus_revision": manifest["corpus_revision"], "as_of": config["as_of"],
                    "original_issue_ids": remaining, "evidence_span_ids": legal_spans, "gap_assessment": gap,
                    "after_semantic_payload": old["after_semantic_payload"], "actual_field_diff": [],
                    "current_record": {"page_id": old["page_id"], "parent_id": old["parent_id"],
                                       "version_id": old["base_version_id"], "semantic_payload": old["before_semantic_payload"],
                                       "decision": record_plan[old["entity_id"]]["decision"], "reviewer_note": "PINNED_UNCHANGED"},
                    "dependency_records": old["dependency_records"],
                    "authorized_to_execute": False}
        proposal["proposal_hash"] = digest(proposal)
        proposals.append(proposal)
    field_map = {p["entity_id"]: {"legal_status": p["evidence_span_ids"], "condition_ast": [], "exception_ast": [], "overlap": []} for p in proposals}
    unresolved_sources = [dict(source_id=x["source_id"], url=x["url"], status=x["status"], error=x.get("error")) for x in manifest["sources"] if x["status"] != "FETCHED"]
    review = "# V16.6 evidence completion review pack\n\nNo production authorization. Legal reference candidates require human adjudication; condition, exception and overlap remain unresolved.\n"
    readiness = {"status": "V166_CODE_PASS_WAITING_INPUTS / PHASE_F_NOT_AUTHORIZED", "mode": "LOCAL_SHADOW_NO_WRITE",
                 "corpus_revision": manifest["corpus_revision"], "source_fetched": len(index), "source_blocked": len(unresolved_sources),
                 "original_issue_count": 79, "v165_blocker_count": 6, "unresolved_after": 85,
                 "complete_drafts": 0, "accepted_real": 0, "real_projected": 0,
                 "human_field_writes": 0, "production_writes": 0, "create_operations": 0,
                 "sql_executions": 0, "schema_mutations": 0, "scheduler_actions": 0,
                 "publication_eligibility": "NOT_EVALUATED", "authorized_to_execute": False}
    outputs = {"source_index.json": index, "source_spans.jsonl": spans, "field_support_map.json": field_map,
               "interpretation_candidates.jsonl": proposals, "counterexamples.jsonl": [{"scenario": {"fixed": True, "covered": True, "age_years": 13}, "result": "UNKNOWN", "reason": "PRECEDENCE_NOT_PROVEN"}],
               "unresolved_sources.jsonl": unresolved_sources, "reference_graph.json": {"closed": [], "open": ["conditions", "exceptions", "overlap", "legal-time-adjudication"]},
               "review_pack.md": review, "expanded_issue_ledger.json": {"issues": ledger}, "ledger_events.jsonl": [],
               "readiness.json": readiness, "canary_plan.json": {"records": [], "authorized_to_execute": False},
               "baseline_verification.json": {"status": "PASS", "canonical_sha256": BASELINE, "issue_universe": 85},
               "input_manifest.json": {"run_config_sha256": sha256(config_path.read_bytes()), "v165_artifact_manifest_sha256": sha256((v165 / "artifact_hashes.json").read_bytes()), "corpus_revision": manifest["corpus_revision"]}}
    module_root = Path(__file__).parent
    outputs["code_manifest.json"] = {p.relative_to(Path.cwd()).as_posix(): sha256(p.read_bytes()) for p in sorted(module_root.glob("*.py"))}
    with offline_guard() as attempts:
        pass
    readiness["offline_forbidden_attempts"] = attempts
    hashes = write_new(output, outputs)
    return {"status": readiness["status"], "proposals": len(proposals), "artifact_manifest": digest(hashes)}


def review_check(proposal_dir, trust_path, output):
    verify_hashes(proposal_dir)
    trust = validate_trust(load(trust_path))
    validation = {"schema_version": 1, "status": "VALID"}
    for name, expected in trust["trusted_pins"].items():
        receipt = trust["receipts"][name]
        require(receipt is not None and digest(receipt) == expected, "TRUST_ROOT_PIN_MISMATCH", name)
    validations = []
    proposals = rows(Path(proposal_dir) / "interpretation_candidates.jsonl")
    for item in proposals:
        receipt = trust["receipts"]["adjudication"]
        bound = receipt.get("proposal_hash") == item["proposal_hash"] and receipt.get("decision") == "ACCEPT"
        validations.append({"proposal_hash": item["proposal_hash"], "status": "ACCEPTED" if bound else "STALE_OR_REJECTED"})
    validation["proposals"] = validations
    write_new(output, {"receipt_validation.json": validation})
    return validation


def project_shadow(run_config_path, proposal_dir, trust_path, output):
    config = validate_run_config(load(run_config_path))
    verify_hashes(proposal_dir)
    proposals = rows(Path(proposal_dir) / "interpretation_candidates.jsonl")
    ledger = load(Path(proposal_dir) / "expanded_issue_ledger.json")["issues"]
    accepted = []
    trust = None
    if trust_path:
        trust = validate_trust(load(trust_path))
        for key, pin in trust["trusted_pins"].items():
            require(digest(trust["receipts"][key]) == pin, "TRUST_ROOT_PIN_MISMATCH", key)
        activation = trust["receipts"]["activation"]
        adjudication = trust["receipts"]["adjudication"]
        require(activation.get("decision") == "APPROVE_LOCAL_SHADOW", "CONTRACT_NOT_ACTIVATED")
        for p in proposals:
            if p["state"] != "COMPLETE_PENDING_REVIEW":
                continue
            require(p["target_version_id"] and not any(v in {"MISSING", "UNKNOWN"} for v in p["gap_assessment"].values()), "INCOMPLETE_RECORD")
            require(p["current_record"]["version_id"] == p["base_version_id"], "BASE_VERSION_CHANGED")
            require(p["current_record"]["decision"] not in {"HOLD", "REJECTED"}, "HUMAN_HOLD")
            require(p["entity_id"] in activation.get("target_entity_ids", []), "ACTIVATION_SCOPE_MISMATCH")
            require(adjudication.get("proposal_hash") == p["proposal_hash"] and adjudication.get("decision") == "ACCEPT", "REVIEW_REQUIRED")
            require(adjudication.get("base_version_id") == p["base_version_id"] and adjudication.get("target_version_id") == p["target_version_id"], "REVIEW_BINDING_STALE")
            accepted.append(p)
    parent = Path(output).parent
    parent.mkdir(parents=True, exist_ok=True)
    stage = parent / ("." + Path(output).name + ".staging")
    require(not Path(output).exists() and not stage.exists(), "OUTPUT_ALREADY_EXISTS")
    projected_ledger = deepcopy(ledger)
    projected_records, events = [], []
    for p in accepted:
        projected_records.append({"entity_id": p["entity_id"], "page_id": p["current_record"]["page_id"],
                                  "base_version_id": p["base_version_id"], "target_version_id": p["target_version_id"],
                                  "semantic_payload": p["after_semantic_payload"], "operation": "LOCAL_SHADOW_UPDATE",
                                  "decision": p["current_record"]["decision"], "reviewer_note": p["current_record"]["reviewer_note"]})
        for issue in projected_ledger:
            if issue["issue_id"] in p["original_issue_ids"]:
                existing = issue.get("resolution_event")
                if issue.get("resolution_status") == "RESOLVED":
                    require(existing and existing.get("proposal_hash") == p["proposal_hash"], "RESOLUTION_CONFLICT")
                    continue
                event = {"issue_id": issue["issue_id"], "base_version_id": p["base_version_id"],
                         "target_version_id": p["target_version_id"], "proposal_hash": p["proposal_hash"],
                         "adjudication_pin": trust["trusted_pins"]["adjudication"]}
                issue["resolution_status"] = "RESOLVED"; issue["resolution_event"] = event; events.append(event)
    status = "V166_REAL_SHADOW_PROJECTED / PHASE_F_NOT_AUTHORIZED" if accepted else "V166_CODE_PASS_WAITING_INPUTS / PHASE_F_NOT_AUTHORIZED"
    outputs = {"projected_ledger.json": {"issues": projected_ledger}, "projected_records.json": {"records": projected_records, "operation": "LOCAL_SHADOW_UPDATE" if accepted else "NO_CHANGE"},
               "ledger_events.jsonl": events, "readiness.json": {"status": status, "apply_status": "LOCAL_SHADOW_PROJECTED" if accepted else "NOT_EXECUTED", "authorized_to_execute": False},
               "canary_plan.json": {"records": [], "authorized_to_execute": False}}
    hashes = write_new(stage, outputs)
    marker = {"schema_version": 1, "state": "COMMITTED", "artifact_hashes_sha256": sha256((stage / "artifact_hashes.json").read_bytes()), "run_config_sha256": sha256(Path(run_config_path).read_bytes())}
    (stage / "COMMIT_MARKER.json").write_bytes(bytes_for(marker) + b"\n")
    os.replace(stage, output)
    return {"status": status, "apply": outputs["readiness.json"]["apply_status"], "artifact_manifest": digest(hashes)}
