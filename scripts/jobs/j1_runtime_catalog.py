"""Runtime inputs J1 cross-checks. Paths only; no mutation of source data."""
from __future__ import annotations

# Copied from src/kf_pilot/machine_admission/pipeline.py LEGACY (read-only catalog).
MACHINE_ADMISSION_LEGACY: dict[str, str] = {
    "baseline": "v162/baseline-reproduced/notion_typed_update_plan.json",
    "mapping": "v164/artifacts/final-003/v164_mapping_snapshot.jsonl",
    "human": "v164/artifacts/final-003/v164_human_audit_snapshot.jsonl",
    "ledger": "v165/artifacts/final-001/projected_issue_ledger.json",
    "original_issues": "v163/artifacts/final-002/v162_issue_ledger.json",
    "blockers": "v165/artifacts/final-001/new_blockers.jsonl",
    "proposals": "v165/artifacts/final-001/complete_record_proposals.jsonl",
    "records": "v165/artifacts/final-001/projected_record_plan.json",
    "aliases": "v162/baseline-reproduced/claim_aliases.jsonl",
}

SAMPLE_INPUT_PATHS: tuple[str, ...] = (
    "sample_input/resource_manifest.csv",
    "sample_input/files/sample-kito-cb010.html",
)

TEST_ONLY_FIXTURES: tuple[str, ...] = (
    "fixtures/v161/current_notion_schema.json",
    "fixtures/v161/legacy_rows.json",
    "fixtures/v161/live_review_snapshot.json",
)

# Pins recorded in v16_migration/v161-inputs/input_manifest.json; parquet is
# outside Git by architecture (see .gitignore and SOURCE_MAP.md).
V161_PARQUET_PINS: dict[str, str] = {
    "knowledge/canonical_knowledge.parquet": (
        "74130d9861f46a00ad82b0870ab8cbbfa2f3a5a42be22687747559eb79f14f05"
    ),
    "review/notion_v2_sync.parquet": (
        "f11b2394e6609e6fb8bfda39e84e36ea8f7af00a576a6b1037f14c10a7f9e6c6"
    ),
}

V161_PARQUET_EXPECTED_ROOT = (
    ".kaggle-deploy/release-20260904/claims-v15-output/kf-pilot-review-output"
)

MIGRATION_ASSETS = "manifests/migration_assets.json"
LEGACY_MANIFEST_MODULE = "src/kf_pilot/legacy_manifest.py"

WINDOWS_LOCATOR_MANIFESTS: tuple[str, ...] = (
    "v162/artifacts/remediation-final/v162_input_manifest.json",
    "v162/artifacts/remediation-final-replay/v162_input_manifest.json",
    "v162/artifacts/remediation-001/v162_input_manifest.json",
    "v162/artifacts/remediation-replay-001/v162_input_manifest.json",
    "v163/artifacts/final-001/v163_input_manifest.json",
    "v163/artifacts/final-002/v163_input_manifest.json",
    "v163/artifacts/replay-001/v163_input_manifest.json",
    "v163/artifacts/replay-002/v163_input_manifest.json",
)

POSIX_FILE_MAP_MANIFESTS: tuple[str, ...] = (
    "v16_migration/v161-inputs/input_manifest.json",
    "v165/artifacts/final-001/input_manifest.json",
    "v165/artifacts/replay-001/input_manifest.json",
)
