"""Offline V15 -> V16 migration. Never reads secrets or calls Notion."""
from pathlib import Path
import argparse
import hashlib
import json
from collections import Counter
import pyarrow.parquet as pq
from kf_pilot.v16.migration import LegacyCanonicalRow, migrate_row
from kf_pilot.v16.notion_payload import build_update_only_plan


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False), encoding="utf-8")


def migrate(rows, run_id):
    results = [migrate_row(row, run_id) for row in rows]
    aliases = {}
    entities = set()
    for result in results:
        entity = result.entity["claim_entity_id"]
        if entity in entities:
            raise ValueError("duplicate legacy entity")
        entities.add(entity)
        for alias in result.aliases:
            key = alias["alias_key"]
            if key in aliases and aliases[key] != entity:
                raise ValueError("alias collision")
            aliases[key] = entity
    plan = build_update_only_plan([r.version for r in results],
        [r.publication_mapping for r in results if r.publication_mapping], run_id=run_id)
    if plan["missing_mapping_count"]:
        raise ValueError("missing page mapping")
    return sorted(results, key=lambda r: r.entity["claim_entity_id"]), plan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    files = {"canonical": args.baseline / "knowledge/canonical_knowledge.parquet",
             "mappings": args.baseline / "review/notion_v2_sync.parquet",
             "decisions": args.baseline / "review/review_decisions.parquet"}
    hashes = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in files.items()}
    canonical = pq.read_table(files["canonical"]).to_pylist()
    mappings = pq.read_table(files["mappings"]).to_pylist()
    decisions = pq.read_table(files["decisions"]).to_pylist()
    if len(canonical) != 70 or len(mappings) != 102:
        raise ValueError("unexpected V15 baseline cardinality")
    knowledge_maps = [r for r in mappings if r["target"] == "KNOWLEDGE_ITEM"]
    pages = {r["candidate_id"]: r["notion_page_id"] for r in knowledge_maps}
    if len(pages) != 70 or len(set(pages.values())) != 70:
        raise ValueError("duplicate/missing knowledge mappings")
    # V15 decisions export is product-only: never infer knowledge approvals from it.
    rows = [LegacyCanonicalRow(
        legacy_canonical_id=r["knowledge_id"], canonical_text=r["canonical_text"],
        product_family=r["subject_product_family"], subject=r["subject_product_family"],
        predicate=r["predicate"],
        object_value={"legacy_claim_text": r["canonical_text"],
                      "numeric_slots": json.loads(r["numeric_slots_json"])},
        jurisdiction=r["jurisdiction"], applicability=r["applicability_scope"],
        legal_status=r["legal_status"], condition_tags=json.loads(r["conditions_json"]),
        system_status=r["decision_state"], notion_page_id=pages[r["knowledge_id"]]
    ) for r in canonical]
    if args.snapshot:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        live = {r["Knowledge ID"]: r for r in snapshot["results"]}
        if len(live) != len(snapshot["results"]):
            raise ValueError("duplicate live Knowledge ID")
        hashes["live_snapshot"] = hashlib.sha256(args.snapshot.read_bytes()).hexdigest()
        for row in rows:
            current = live[row.legacy_canonical_id]
            if current["url"].rstrip("/").split("/")[-1].replace("-", "") != row.notion_page_id.replace("-", ""):
                raise ValueError("live page mapping drift")
            row.decision = current["Decision"] or "PENDING"
            row.notes = current["Reviewer Note"]
            if current["Status"] in {"HOLD", "REJECTED"}:
                row.system_status = current["Status"]
    run_id = "v16-" + hashes["canonical"][:16]
    a, plan = migrate(rows, run_id)
    b, _ = migrate(list(reversed(rows)), run_id)
    assert [r.entity for r in a] == [r.entity for r in b]
    assert [r.version for r in a] == [r.version for r in b]
    changed = rows[0].model_copy(update={"condition_ast": {"op": "FALSE"}})
    c, _ = migrate([changed] + rows[1:], run_id)
    assert [r.entity["claim_entity_id"] for r in a] == [r.entity["claim_entity_id"] for r in c]
    assert sum(x.version["claim_version_id"] != y.version["claim_version_id"] for x,y in zip(a,c)) == 1
    assert [r.publication_mapping for r in a] == [r.publication_mapping for r in c]
    collections = {"claim_entities": [r.entity for r in a], "claim_versions": [r.version for r in a],
        "claim_aliases": [x for r in a for x in r.aliases], "decision_bindings": [r.decision_binding for r in a],
        "publication_mappings": [r.publication_mapping for r in a], "migration_issues": [x for r in a for x in r.issues],
        "v15_all_page_mappings": mappings, "v15_exported_decisions": decisions}
    for name, items in collections.items():
        (args.output / (name + ".jsonl")).write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True, allow_nan=False)+"\n" for x in items), encoding="utf-8")
    plan["publication_ready"] = False
    plan["blocking_reason"] = "Complete live human decision/notes snapshot and Notion schema validation required"
    dump(args.output / "notion_no_write_plan.json", plan)
    report = {"mode": "NO_WRITE", "baseline_sha256": hashes, "entity_count": len(a),
        "planned_updates": plan["updated_count"], "planned_creates": 0,
        "condition_unresolved_count": sum(r.version["condition_unresolved"] for r in a),
        "effective_decisions": dict(Counter(r.decision_binding["effective_decision"] for r in a)),
        "row_order_replay": "PASS", "single_semantic_change": "PASS", "page_mapping_replay": "PASS",
        "production_writes": 0, "live_decision_note_snapshot": bool(args.snapshot),
        "limitations": ["V15 decision export is not a complete live knowledge review snapshot",
            "Legacy text retained in object value: structured semantic extraction remains pending",
            "SQL reference not applied; payload is a logical plan, not a validated HTTP request"]}
    dump(args.output / "migration_report.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
