"""Public-API mapping only. Contractor baseline pinned by SHA.

If a required seam is missing from contractor public __all__, propose a
reviewer-owned diff instead of patching contractor source from this job.
"""

from __future__ import annotations

CONTRACTOR_REPO = "trunghungvtcn/pipeline-lab-contractor-m1-m5"
CONTRACTOR_BASELINE = "afac091e60bb6c8a0f0630964e43f5e80951267c"
FACTORY_BASELINE = "3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b"
J1_REVIEWED = "b9e291fb84ddf99a6e6dd662ae122f39326f4d41"
J2_PUBLISHED = "5e6161914f519403059ce13a1568d58ac7162f28"

# KF runtime contract field / action -> contractor public symbol
SYMBOL_MAP: dict[str, dict[str, str]] = {
    "RunContract.fingerprint": {
        "module": "kf_pilot.runtime_contract",
        "symbol": "RunContract.fingerprint",
        "contractor": "JobLedger.admit(idempotency_key, request_digest)",
        "notes": "fingerprint is the idempotency key; request_digest binds snapshot + J1/J2 commit SHA + input hash",
    },
    "RunContract.code_commit": {
        "module": "kf_pilot.runtime_contract",
        "symbol": "RunContract.code_commit",
        "contractor": "not stored by JobLedger; echoed on ShadowResult only",
        "notes": "J3 does not mutate contractor schema",
    },
    "RunContract.input_manifest_sha256": {
        "module": "kf_pilot.runtime_contract",
        "symbol": "RunContract.input_manifest_sha256",
        "contractor": "LocatorResolver.resolve(expected_sha256) + SourceRef.expected_sha256",
        "notes": "hash mismatch is fail-closed",
    },
    "RunContract.attempt_budget": {
        "module": "kf_pilot.runtime_contract",
        "symbol": "RunContract.attempt_budget",
        "contractor": "JobLedger.reserve_budget(amount, reservation_id)",
        "notes": "amount is attempt_budget; reservation_id is fingerprint prefix",
    },
    "RunContract.mode": {
        "module": "kf_pilot.runtime_contract",
        "symbol": "RunContract.mode",
        "contractor": "gate in LocalShadowAdapter; TEST_ONLY required",
        "notes": "non-TEST_ONLY is HUMAN_HOLD, never forwarded",
    },
    "execute_test_only": {
        "module": "kf_pilot.runtime_contract",
        "symbol": "execute_test_only",
        "contractor": "LocalShadowAdapter.run",
        "notes": "shadow path uses ledger+store; does not replace execute_test_only",
    },
}

PUBLIC_API_MAP: dict[str, dict[str, str]] = {
    "grok_locator.LocatorResolver": {
        "package": "grok_locator",
        "symbols": "LocatorResolver, LocatorProfile, LocatorError, DefaultFS",
        "used": "validate + resolve snapshot under work root",
    },
    "grok_asset_store.AssetStore": {
        "package": "grok_asset_store",
        "symbols": "AssetStore, SourceRef, DictReader",
        "used": "freeze verified snapshot bytes; verify_manifest after freeze",
    },
    "grok_job_ledger.JobLedger": {
        "package": "grok_job_ledger",
        "symbols": "JobLedger.admit/claim/record_attempt/finalize/reserve_budget/get/history",
        "used": "durable local SQLite ledger in work_root/jobs.db",
    },
    "grok_notion_projection.Projector": {
        "package": "grok_notion_projection",
        "symbols": "Projector.project, FakeTransport, MUTATING_OPS, READ_OPS",
        "used": "LOCAL_SHADOW projection only after LOCAL_SHADOW_ALLOWED marker",
    },
}

SEAM_PROPOSALS: list[dict[str, str]] = [
    {
        "gap": "JobLedger has no column for factory code_commit / dataset_snapshot_id",
        "proposal": "Keep those fields on ShadowResult only; do not alter contractor schema from J3",
        "owner": "reviewer",
    },
    {
        "gap": "J1/J2 input content hashes are unpublished; only commit SHAs are published",
        "proposal": "Bind commit SHA and input hash separately; input_verified stays false until inventory digest exists",
        "owner": "J1/J2 authors",
    },
]
