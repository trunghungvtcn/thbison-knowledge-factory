from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kf_pilot.v16.migration import LegacyCanonicalRow, migrate_row  # noqa: E402
from kf_pilot.v16.notion_payload import build_update_only_plan  # noqa: E402
from kf_pilot.v16.notion_adapter import notion_schema_diff  # noqa: E402
from kf_pilot.v16.decision_pull import LiveReviewSnapshot, bind_live_decision  # noqa: E402
from kf_pilot.v16.decisions import effective_decision  # noqa: E402


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-id", default="V16-DRY-RUN")
    parser.add_argument("--notion-schema")
    parser.add_argument("--live-review-snapshot")
    parser.add_argument("--expected-count", type=int)
    args = parser.parse_args()

    input_path = Path(args.input)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    raw_rows = json.loads(input_path.read_text(encoding="utf-8"))
    if not raw_rows or (args.expected_count is not None and len(raw_rows) != args.expected_count):
        raise RuntimeError("unexpected input cardinality")
    results = [migrate_row(LegacyCanonicalRow.model_validate(row), args.run_id) for row in raw_rows]

    entities = [result.entity for result in results]
    versions = [result.version for result in results]
    aliases = [item for result in results for item in result.aliases]
    decisions = [result.decision_binding for result in results]
    mappings = [result.publication_mapping for result in results if result.publication_mapping]
    issues = [item for result in results for item in result.issues]

    if args.live_review_snapshot:
        raw_snapshots = json.loads(Path(args.live_review_snapshot).read_text(encoding="utf-8"))
        snapshots: dict[str, LiveReviewSnapshot] = {}
        for raw in raw_snapshots:
            snapshot = LiveReviewSnapshot(**raw)
            if snapshot.legacy_id in snapshots:
                raise RuntimeError(f"duplicate live snapshot legacy ID: {snapshot.legacy_id}")
            snapshots[snapshot.legacy_id] = snapshot
        decisions = []
        mapping_by_entity = {row["claim_entity_id"]: row for row in mappings}
        for version in versions:
            legacy_id = version["legacy_canonical_id"]
            if legacy_id not in snapshots:
                raise RuntimeError(f"missing live review snapshot: {legacy_id}")
            mapping = mapping_by_entity.get(version["claim_entity_id"])
            if mapping is None:
                raise RuntimeError(f"missing page mapping for live decision: {legacy_id}")
            binding = bind_live_decision(
                snapshot=snapshots[legacy_id],
                mapped_page_id=mapping["remote_page_id"],
                claim_entity_id=version["claim_entity_id"],
            )
            # Live review status takes precedence over an older export.
            if snapshots[legacy_id].status in {"HOLD", "REJECTED"}:
                version["source_system_status"] = snapshots[legacy_id].status
            decisions.append(
                {
                    "claim_entity_id": version["claim_entity_id"],
                    "reviewed_claim_version_id": binding.reviewed_claim_version_id,
                    "decision": binding.decision,
                    "effective_decision": effective_decision(
                        system_status=version["source_system_status"],
                        current_claim_version_id=version["claim_version_id"],
                        binding=binding,
                        condition_unresolved=version["condition_unresolved"],
                    ),
                    "notes": binding.notes,
                }
            )

    # Unstructured object values cannot remain effectively approved.
    version_by_entity = {v["claim_entity_id"]: v for v in versions}
    for binding in decisions:
        if binding["effective_decision"] == "APPROVED" and not version_by_entity[binding["claim_entity_id"]]["object_value_structured"]:
            binding["effective_decision"] = "HOLD_OBJECT_VALUE_REVIEW"

    alias_owners: dict[str, str] = {}
    for alias in aliases:
        current = alias_owners.setdefault(alias["alias_key"], alias["claim_entity_id"])
        if current != alias["claim_entity_id"]:
            raise RuntimeError(f"alias conflict: {alias['alias_key']}")

    write_jsonl(output / "claim_entities.jsonl", entities)
    write_jsonl(output / "claim_versions.jsonl", versions)
    write_jsonl(output / "claim_aliases.jsonl", aliases)
    write_jsonl(output / "decision_bindings.jsonl", decisions)
    write_jsonl(output / "publication_mappings.jsonl", mappings)
    write_jsonl(output / "migration_issues.jsonl", issues)
    notion_plan = build_update_only_plan(
        versions, mappings, run_id=args.run_id, bindings=decisions
    )
    (output / "notion_typed_update_plan.json").write_text(
        json.dumps(notion_plan, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    schema = {}
    if args.notion_schema:
        schema = json.loads(Path(args.notion_schema).read_text(encoding="utf-8"))
    schema_report = notion_schema_diff(schema)
    (output / "notion_schema_diff.json").write_text(
        json.dumps(schema_report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    human_fields = {"Decision", "Reviewer Note", "Reviewed Entity ID", "Reviewed Version ID"}
    human_field_writes = sum(
        bool(set(operation["typed_properties"]) & human_fields)
        for operation in notion_plan["operations"]
    )
    effective_counts: dict[str, int] = {}
    for binding in decisions:
        state = binding["effective_decision"]
        effective_counts[state] = effective_counts.get(state, 0) + 1
    prepublication = {
        "mode": "NO_WRITE",
        "input_rows": len(raw_rows),
        "update_count": notion_plan["updated_count"],
        "create_count": notion_plan["created_count"],
        "missing_mapping_count": notion_plan["missing_mapping_count"],
        "mapping_collision_count": notion_plan["mapping_collision_count"],
        "human_field_write_count": human_field_writes,
        "blocking_issue_count": sum(1 for issue in issues if issue.get("blocking")),
        "effective_decision_counts": dict(sorted(effective_counts.items())),
        "schema_type_mismatch_count": len(schema_report["type_mismatches"]),
        "remote_writes": 0,
        "ready_for_remote_no_write": (
            notion_plan["updated_count"] == len(raw_rows)
            and notion_plan["created_count"] == 0
            and notion_plan["missing_mapping_count"] == 0
            and human_field_writes == 0
            and not schema_report["type_mismatches"]
        ),
        "production_mutation_authorized": False,
    }
    (output / "prepublication_validation_report.json").write_text(
        json.dumps(prepublication, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    report = {
        "run_id": args.run_id,
        "input_rows": len(raw_rows),
        "entities": len(entities),
        "versions": len(versions),
        "aliases": len(aliases),
        "publication_mappings": len(mappings),
        "blocking_issues": sum(1 for issue in issues if issue.get("blocking")),
        "remote_writes": 0,
        "notion_created": notion_plan["created_count"],
        "notion_updates_planned": notion_plan["updated_count"],
        "missing_page_mappings": notion_plan["missing_mapping_count"],
        "status": "DRY_RUN_COMPLETE",
    }
    (output / "migration_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
