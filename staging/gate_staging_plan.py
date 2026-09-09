from __future__ import annotations

import argparse
import json
from pathlib import Path

HUMAN_OWNED = {"Decision", "Reviewer Note", "Reviewed Entity ID", "Reviewed Version ID"}


def fail(msg: str) -> None:
    raise SystemExit(f"STAGING_PLAN_GATE_FAIL: {msg}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", type=Path)
    args = ap.parse_args()
    data = json.loads(args.plan.read_text(encoding="utf-8"))
    if data.get("target_kind") != "DEDICATED_STAGING":
        fail("target_kind must be DEDICATED_STAGING")
    records = data.get("records")
    if not isinstance(records, list) or not (1 <= len(records) <= 3):
        fail("plan must contain 1..3 records")
    seen = set()
    for i, rec in enumerate(records, 1):
        if rec.get("operation") != "UPDATE":
            fail(f"record {i}: only UPDATE is allowed")
        if rec.get("environment") != "STAGING":
            fail(f"record {i}: environment must be STAGING")
        if rec.get("synthetic") is not True:
            fail(f"record {i}: synthetic=true is required")
        sid = rec.get("synthetic_id")
        if not isinstance(sid, str) or not sid.startswith("V161-STAGING-SYNTH-"):
            fail(f"record {i}: invalid synthetic_id")
        if sid in seen:
            fail(f"record {i}: duplicate synthetic_id")
        seen.add(sid)
        target = rec.get("target_ref", "")
        if not isinstance(target, str) or not target.startswith("STAGING_FIXTURE_PAGE_"):
            fail(f"record {i}: target_ref is not an isolated staging fixture")
        props = rec.get("properties")
        if not isinstance(props, dict):
            fail(f"record {i}: properties must be an object")
        forbidden = HUMAN_OWNED.intersection(props)
        if forbidden:
            fail(f"record {i}: human-owned fields present: {sorted(forbidden)}")
        sem = rec.get("semantic_fixture", {})
        ov = sem.get("object_value", {})
        if ov.get("type") not in {"quantity", "enum", "boolean"}:
            fail(f"record {i}: object_value is not structured")
        if sem.get("condition_ast") != {"op": "TRUE"}:
            fail(f"record {i}: unresolved/nontrivial condition in synthetic fixture")
    print(f"STAGING_PLAN_GATE_PASS: {len(records)} synthetic UPDATE records; 0 human-owned fields")


if __name__ == "__main__":
    main()
