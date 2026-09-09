#!/usr/bin/env python3
import argparse, hashlib, json, sys
from collections import Counter

ISSUE_TYPES = {"OBJECT_VALUE_UNSTRUCTURED", "CONDITION_CONNECTIVE_AMBIGUOUS"}
STATUSES = {"RESOLVED", "HOLD", "NEEDS_REVIEW"}


def fail(msg):
    raise SystemExit("REMEDIATION_LEDGER_GATE_FAIL: " + msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ledger")
    ap.add_argument("--expected-total", type=int, default=79)
    ap.add_argument("--expected-object", type=int, default=70)
    ap.add_argument("--expected-condition", type=int, default=9)
    args = ap.parse_args()
    with open(args.ledger, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("issues") if isinstance(data, dict) else data
    if not isinstance(rows, list): fail("ledger must be a list or {'issues': [...]} object")
    if len(rows) != args.expected_total: fail(f"expected {args.expected_total} issues, got {len(rows)}")
    ids, keys = set(), set(); counts = Counter(); statuses = Counter()
    for i, r in enumerate(rows):
        if not isinstance(r, dict): fail(f"row {i} is not an object")
        iid = r.get("issue_id")
        if not iid or iid in ids: fail(f"missing/duplicate issue_id at row {i}: {iid!r}")
        ids.add(iid)
        typ = r.get("issue_type")
        if typ not in ISSUE_TYPES: fail(f"invalid issue_type for {iid}: {typ!r}")
        counts[typ] += 1
        key = (r.get("entity_id"), r.get("version_id"), typ)
        if None in key or key in keys: fail(f"missing/duplicate entity-version-type key for {iid}: {key}")
        keys.add(key)
        status = r.get("resolution_status")
        if status not in STATUSES: fail(f"invalid resolution_status for {iid}: {status!r}")
        statuses[status] += 1
        if not r.get("before_value_hash"): fail(f"missing before_value_hash for {iid}")
        if status == "RESOLVED":
            if not r.get("source_evidence_refs"): fail(f"resolved item missing evidence refs: {iid}")
            if not r.get("resolution_rule"): fail(f"resolved item missing deterministic rule: {iid}")
            if not r.get("after_value_hash"): fail(f"resolved item missing after hash: {iid}")
            if typ == "OBJECT_VALUE_UNSTRUCTURED" and r.get("structured_value") is None:
                fail(f"resolved object issue missing structured_value: {iid}")
            if typ == "CONDITION_CONNECTIVE_AMBIGUOUS" and r.get("condition_ast") is None:
                fail(f"resolved condition issue missing condition_ast: {iid}")
        else:
            if not r.get("review_reason"): fail(f"unresolved item missing review_reason: {iid}")
    if counts["OBJECT_VALUE_UNSTRUCTURED"] != args.expected_object:
        fail(f"expected {args.expected_object} object issues, got {counts['OBJECT_VALUE_UNSTRUCTURED']}")
    if counts["CONDITION_CONNECTIVE_AMBIGUOUS"] != args.expected_condition:
        fail(f"expected {args.expected_condition} condition issues, got {counts['CONDITION_CONNECTIVE_AMBIGUOUS']}")
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    print(f"REMEDIATION_LEDGER_GATE_PASS total={len(rows)} resolved={statuses['RESOLVED']} hold={statuses['HOLD']} needs_review={statuses['NEEDS_REVIEW']} sha256={digest}")

if __name__ == "__main__": main()
