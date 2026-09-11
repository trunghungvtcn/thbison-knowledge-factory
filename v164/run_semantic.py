"""Repository adapter and deterministic V16.4 NO_WRITE runner.

This module only reads the pinned V16.1/V16.2/V16.3 repository state and raw
source files.  It has no network or mutation transport.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kf_pilot.v16.identity import claim_version_id
from kf_pilot.legacy_manifest import LegacyManifestPathError, resolve_manifest_entries
from kf_pilot.v162_remediation.core import BASELINE, compute, digest as v162_digest, resolve
from kf_pilot.v163_evidence.binding import digest as v163_digest
from kf_pilot.v163_evidence.sources import VisibleText, source_catalog, verify_span
from kf_pilot.v164_semantics.artifacts import output_bytes, write_artifacts
from kf_pilot.v164_semantics.canonical import GateError, digest, load_json, require, sha256
from kf_pilot.v164_semantics.integration import Compatibility, Runtime
from kf_pilot.v164_semantics.pipeline import ASSETS, run as semantic_run

V163_FINAL = ROOT / "v163/artifacts/final-002"
V163_REPLAY = ROOT / "v163/artifacts/replay-002"
V162_BASE = ROOT / "v162/baseline-reproduced"
BASELINE_FILE = V162_BASE / "notion_typed_update_plan.json"
IDENTITY_CONTRACT = "kf_pilot.v16.identity.claim_version_id/v1"
PARENT = "9d53865d0cdd41f3a6c65d171b4e50f4"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _verify_manifest(directory: Path) -> None:
    manifest = _json(directory / "artifact_hashes.json")
    actual = {p.name for p in directory.iterdir() if p.is_file()}
    require(actual == set(manifest) | {"artifact_hashes.json"}, "V163_ARTIFACT_ACCOUNTING_MISMATCH")
    for name, expected in manifest.items():
        require(sha256((directory / name).read_bytes()) == expected, "V163_ARTIFACT_HASH_MISMATCH", name)


def verify_checkpoint() -> dict:
    _verify_manifest(V163_FINAL)
    _verify_manifest(V163_REPLAY)
    left = {p.name for p in V163_FINAL.iterdir() if p.is_file()}
    right = {p.name for p in V163_REPLAY.iterdir() if p.is_file()}
    require(left == right, "V163_REPLAY_FILESET_MISMATCH")
    for name in sorted(left):
        require((V163_FINAL / name).read_bytes() == (V163_REPLAY / name).read_bytes(),
                "V163_REPLAY_BYTES_MISMATCH", name)
    plan = _json(BASELINE_FILE)
    require(v162_digest(plan) == BASELINE, "V161_BASELINE_MISMATCH")
    source_manifest = _json(V163_FINAL / "v163_input_manifest.json")
    try:
        source_paths = resolve_manifest_entries(ROOT, source_manifest, dialect="windows-relative-v1")
    except LegacyManifestPathError as exc:
        require(False, "V163_INPUT_MANIFEST_PATH_UNSAFE", str(exc))
    for rel, expected in source_manifest.items():
        path = source_paths[rel]
        require(path.is_file() and sha256(path.read_bytes()) == expected,
                "V163_INPUT_MANIFEST_MISMATCH", rel)
    report = _json(V163_FINAL / "v163_readiness_report.json")
    require(report["authoritative_issue_count"] == 79, "V163_ISSUE_COUNT_MISMATCH")
    require(report["binding_candidate_count"] == 5, "V163_CANDIDATE_COUNT_MISMATCH")
    return {"baseline": v162_digest(plan), "v163_manifest": digest(_json(V163_FINAL / "artifact_hashes.json"))}


def _extractors(catalog: dict) -> dict:
    result = {}
    for source in catalog.values():
        extractor_id = source["extractor"]
        if extractor_id.startswith("pymupdf:"):
            def pdf_units(raw: bytes):
                import pymupdf
                with pymupdf.open(stream=raw, filetype="pdf") as pdf:
                    # V16.3 locator page N maps to zero-based pdf index N-1.
                    return {f"pdf:page:{index + 1}": pdf[index].get_text(sort=True)
                            for index in range(len(pdf))}
            result[extractor_id] = pdf_units
        elif extractor_id.startswith("stdlib.HTMLParser:"):
            def html_units(raw: bytes):
                parser = VisibleText()
                parser.feed(raw.decode("utf-8"))
                return {"html:visible-text": " ".join(parser.parts)}
            result[extractor_id] = html_units
    return result


def _span(source: dict, catalog: dict) -> dict:
    verify_span(source, catalog)
    unit, offsets = source["locator"].rsplit(":chars:", 1)
    start, end = (int(value) for value in offsets.split(":"))
    spec = catalog[source["source_ref"]]
    return {"source_ref": source["source_ref"], "raw_sha256": source["content_sha256"],
            "extractor_id": spec["extractor"], "unit_id": unit,
            "start": start, "end": end, "quote": source["exact_quote"]}


def _subspan(parent: dict, start: int, end: int) -> dict:
    value = dict(parent)
    value["start"] = parent["start"] + start
    value["end"] = parent["start"] + end
    value["quote"] = parent["quote"][start:end]
    return value


def build_assets() -> tuple[dict, dict, Runtime, dict]:
    checkpoint = verify_checkpoint()
    versions = _jsonl(V162_BASE / "claim_versions.jsonl")
    plan = _json(BASELINE_FILE)
    operations = {row["claim_entity_id"]: row for row in plan["operations"]}
    ledger = _json(V163_FINAL / "v162_issue_ledger.json")["issues"]
    work = _jsonl(V163_FINAL / "v163_review_pack.jsonl")
    bindings = _jsonl(V163_FINAL / "v163_binding_candidates.jsonl")
    v_by_entity = {row["claim_entity_id"]: row for row in versions}
    work_by_issue = {row["issue_id"]: row for row in work}
    binding_by_id = {row["binding_id"]: row for row in bindings}
    require(len(v_by_entity) == 70 and len(ledger) == len(work) == 79, "NORMALIZATION_COUNT_MISMATCH")
    require(len(bindings) == len(binding_by_id) == 5, "BINDING_COUNT_MISMATCH")

    catalog = source_catalog(ROOT)
    used_refs = sorted({row["source"]["source_ref"] for row in bindings})
    sources = [{"source_ref": ref, "path": catalog[ref]["path"],
                "raw_sha256": catalog[ref]["content_sha256"],
                "extractor_id": catalog[ref]["extractor"]} for ref in used_refs]
    records = []
    for entity, version in sorted(v_by_entity.items()):
        op = operations[entity]
        related = [row for row in ledger if row["entity_id"] == entity]
        first = related[0] if related else {}
        records.append({"entity_id": entity, "version_id": version["claim_version_id"],
                        "page_id": op["page_id"], "parent_id": PARENT,
                        "canonical_text": version["canonical_text"],
                        "system_status": version["source_system_status"],
                        "decision": first.get("decision_snapshot", "PENDING"),
                        "reviewer_note": first.get("reviewer_note_snapshot") or "",
                        "semantic_payload": deepcopy(version["semantic_payload"])})
    issues = [{"issue_id": row["issue_id"], "issue_type": row["issue_type"],
               "entity_id": row["entity_id"], "version_id": row["version_id"],
               "state": row["resolution_status"], "before_value_hash": row["before_value_hash"],
               "source_text": row["source_text"]} for row in ledger]

    candidates = []
    enum_codes = {"overload_prohibition": "OVERLOAD_PROHIBITED",
                  "people_lifting_prohibition": "PEOPLE_LIFTING_PROHIBITED"}
    for binding in sorted(bindings, key=lambda row: row["issue_id"]):
        item = work_by_issue[binding["issue_id"]]
        context = _span(binding["source"], catalog)
        if binding["interpretation"]["kind"] == "quantity":
            amount = binding["interpretation"]["value"]
            match = re.search(rf"(?<![\d.]){re.escape(amount)}\s+(năm)(?!\w)", context["quote"])
            require(match is not None, "QUANTITY_PROOF_NOT_FOUND", binding["issue_id"])
            a0, a1 = match.span(0)[0], match.span(0)[0] + len(amount)
            u0, u1 = match.span(1)
            interpretation = {"kind": "quantity", "amount": amount,
                              "unit": "year", "operator": "EQ"}
            proofs = {"amount": _subspan(context, a0, a1), "unit": _subspan(context, u0, u1)}
        else:
            interpretation = {"kind": "enum", "code": enum_codes[binding["predicate"]],
                              "vocabulary_id": "v164-prohibition-v1"}
            proofs = {"statement": deepcopy(context)}
        candidate = {"candidate_id": "v164_" + binding["binding_id"],
                     "upstream_binding_hash": binding["binding_id"],
                     "issue_id": binding["issue_id"], "entity_id": binding["record_id"],
                     "base_version_id": binding["version_id"], "predicate": binding["predicate"],
                     "applicability": v_by_entity[binding["record_id"]]["semantic_payload"]["applicability"],
                     "proposer_id": "KF_V163_EVIDENCE_BINDER", "context_span": context,
                     "interpretation": interpretation, "proofs": proofs}
        candidates.append(candidate)

    predicates = {}
    for binding in bindings:
        predicate = binding["predicate"]
        if binding["interpretation"]["kind"] == "quantity":
            predicates[predicate] = {"allowed_kinds": ["quantity"], "operators": ["EQ"],
                                     "units": {"year": {"dimension": "time", "source_literals": ["năm"]}},
                                     "vocabulary_ids": []}
        else:
            predicates[predicate] = {"allowed_kinds": ["enum"], "operators": [], "units": {},
                                     "vocabulary_ids": ["v164-prohibition-v1"]}
    assets = {
        "snapshot": {"schema": "v164-normalized/v1", "data_class": "REPOSITORY",
                     "as_of": "2026-09-05T00:00:00Z",
                     "baseline": {"path": str(BASELINE_FILE.relative_to(ROOT)),
                                  "sha256": sha256(BASELINE_FILE.read_bytes())},
                     "identity_contract_id": IDENTITY_CONTRACT, "sources": sources,
                     "records": records, "issues": issues, "candidates": candidates},
        "predicate_contracts": {"data_class": "REPOSITORY", "predicates": predicates},
        # Deliberately empty: candidate wording is not an authoritative vocabulary.
        "vocabularies": {"data_class": "REPOSITORY", "entries": {}},
        "reviewer_registry": {"data_class": "REPOSITORY", "entries": {}},
        "adjudications": {"data_class": "REPOSITORY", "entries": []},
    }
    pins = {name: digest(assets[name]) for name in sorted(ASSETS)}

    def verify_upstream(candidate: dict, issue: dict) -> None:
        binding = binding_by_id.get(candidate["upstream_binding_hash"])
        require(binding is not None, "UPSTREAM_BINDING_NOT_FOUND")
        require(binding["binding_id"] == v163_digest({k: v for k, v in binding.items() if k != "binding_id"}),
                "UPSTREAM_BINDING_HASH_MISMATCH")
        require((binding["issue_id"], binding["record_id"], binding["version_id"], binding["predicate"]) ==
                (issue["issue_id"], candidate["entity_id"], candidate["base_version_id"], candidate["predicate"]),
                "UPSTREAM_BINDING_IDENTITY_MISMATCH")
        require(binding["applicability"] == work_by_issue[issue["issue_id"]]["applicability"],
                "UPSTREAM_APPLICABILITY_MISMATCH")
        verify_span(binding["source"], catalog)

    def check_v162(issue: dict, proposal: dict) -> Compatibility:
        literal = issue["source_text"].strip()
        evidence = {"entity_id": issue["entity_id"], "version_id": issue["version_id"],
                    "field": "object_value", "ref": proposal["context_span"]["source_ref"],
                    "content": literal, "literal": literal,
                    "content_sha256": hashlib.sha256(literal.encode()).hexdigest(),
                    "scope_verified": True, "authoritative": True}
        compatible = resolve({**issue, "source_text": issue["source_text"]}, evidence) is not None
        return Compatibility(compatible, "V162_INPUT_COMPATIBLE" if compatible else "V162_CONTRACT_INCOMPATIBLE")

    runtime = Runtime("REPOSITORY", IDENTITY_CONTRACT, claim_version_id, verify_upstream, check_v162)
    return assets, pins, runtime, {"catalog": catalog, "checkpoint": checkpoint}


def compute_outputs() -> dict:
    assets, pins, runtime, context = build_assets()
    outputs = semantic_run(assets, pins, root=ROOT, runtime=runtime,
                           extractors=_extractors(context["catalog"]))
    report = outputs["v164_readiness_report.json"]
    report.update(status="V164_SEMANTIC_PIPELINE_PASS", repository_acceptance="INTEGRATED_GATES_PASS",
                  baseline_before=BASELINE, baseline_after=v162_digest(_json(BASELINE_FILE)),
                  post_v162_reconciliation="EMPTY_REPLAY_PASS")
    report["proposal_block_reasons"] = {
        reason: sum(row["reason"] == reason for row in outputs["v164_candidate_diagnostics.jsonl"])
        for reason in sorted({row["reason"] for row in outputs["v164_candidate_diagnostics.jsonl"] if row["reason"]})}
    old = _json(V163_FINAL / "v162_readiness_report.json")
    outputs["v164_post_v162_reconciliation.json"] = {
        "status": "EMPTY_REPLAY_PASS", "reason": "NO_ACCEPTED_OR_COMPATIBLE_ADAPTER_INPUT",
        "input_issue_count": len(outputs["v164_issue_accounting.jsonl"]),
        "output_issue_count": old["unresolved_issue_count"], "resolved_delta": 0,
        "resolution_counts": old["resolution_counts"], "baseline_sha256": BASELINE}
    outputs["v164_contract_gap_report.json"].update(
        v162_required="whole original object literal",
        v164_derivation="evidence-bound prose-to-scalar quantity or approved enum",
        interval_compatibility="V162_CONTRACT_INCOMPATIBLE",
        prohibition_vocabulary="AUTHORITATIVE_VOCABULARY_MISSING",
        pdf_page_mapping={"locator": "pdf:page:67", "pdf_zero_based_index": 66,
                          "printed_page_label": 68})
    outputs["v164_phase_f_canary_plan.json"] = {
        "records": [], "authorized_to_execute": False,
        "reason": "ZERO_ACCEPTED_DERIVATIONS_AND_PHASE_F_NOT_AUTHORIZED"}
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="V16.4 repository NO_WRITE semantic remediation")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    outputs = compute_outputs()
    code_paths = sorted((ROOT / "src/kf_pilot/v164_semantics").glob("*.py")) + [Path(__file__)]
    code_manifest = {str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path.read_bytes())
                     for path in code_paths}
    write_artifacts(args.output, outputs, code_manifest)
    print(json.dumps(outputs["v164_readiness_report.json"], ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
