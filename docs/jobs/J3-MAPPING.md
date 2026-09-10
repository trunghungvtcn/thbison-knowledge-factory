# J3 symbol / API mapping

Contractor baseline: `afac091e60bb6c8a0f0630964e43f5e80951267c`

Factory working baseline: `3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b`

Authoritative table: `src/kf_pilot/contractor_bridge/mapping.py`.

## Contractor public `__all__` (inspected, not copied)

- grok_locator: DefaultFS, LocatorError, LocatorProfile, LocatorResolver, dumps_canonical, envelope, loads_strict, reject_syntax
- grok_asset_store: AssetStore, Crash, DictReader, SourceRef, dumps_canonical, envelope, loads_strict
- grok_job_ledger: JobLedger, dumps_canonical, envelope, loads_strict
- grok_notion_projection: FakeTransport, MAPPING_REGISTRY, MUTATING_OPS, Projector, READ_OPS, SnapshotReceipt, TransportError, acquire_snapshot, build_receipt, dumps_canonical, envelope, loads_strict, redact

## Seam proposals (reviewer decides)

1. JobLedger schema has no factory `code_commit` column. J3 echoes it on ShadowResult only.
2. J1/J2 SHAs unpublished. Adapter fail-closes to HUMAN_HOLD rather than inventing pins.
