#!/usr/bin/env python3
import argparse, json
BASELINE = "af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399"
HUMAN = {"Decision", "Reviewer Note", "Reviewed Entity ID", "Reviewed Version ID"}

def fail(msg): raise SystemExit("PHASE_F_READINESS_GATE_FAIL: " + msg)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("report"); ap.add_argument("canary"); a=ap.parse_args()
    with open(a.report, encoding="utf-8") as f: r=json.load(f)
    with open(a.canary, encoding="utf-8") as f: c=json.load(f)
    if r.get("v161_baseline_hash_before") != BASELINE or r.get("v161_baseline_hash_after") != BASELINE:
        fail("V16.1 baseline hash mismatch")
    for k in ("production_write_count","human_field_write_count","create_count","sql_count","scheduler_action_count","schema_mutation_count"):
        if r.get(k,0) != 0: fail(f"{k} must be zero")
    rows=c.get("records",[]) if isinstance(c,dict) else c
    if not isinstance(rows,list) or len(rows)>3: fail("canary must contain 0..3 records")
    if isinstance(c,dict) and c.get("authorized_to_execute") is not False: fail("authorized_to_execute must be false")
    seen=set()
    for x in rows:
        if x.get("operation") != "UPDATE": fail("canary operation must be UPDATE")
        pid=x.get("page_id")
        if not pid or pid in seen: fail("missing/duplicate page_id")
        seen.add(pid)
        if x.get("unresolved_blocker_count",0) != 0: fail(f"unresolved blocker on {pid}")
        if x.get("live_decision") in {"HOLD","REJECTED"}: fail(f"blocked human decision on {pid}")
        fields=set((x.get("field_delta") or {}).keys())
        if fields & HUMAN: fail(f"human-owned field in canary {pid}: {sorted(fields & HUMAN)}")
        for k in ("before_image_hash","expected_after_image_hash","rollback_hash","target_parent_proof"):
            if not x.get(k): fail(f"missing {k} for {pid}")
    print(f"PHASE_F_READINESS_GATE_PASS canary_records={len(rows)} authorized_to_execute=false")

if __name__=="__main__": main()
