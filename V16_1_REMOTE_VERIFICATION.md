# V16.1 remote verification — execution record

## Latest result: PASS — version 2, NO_WRITE only

The single separately authorized retry completed on Kaggle. Outputs were downloaded to `.kaggle-deploy/v161-no-write/remote-v2-output` and independently parsed and compared locally, not merely accepted from the notebook's PASS flag.

| Required gate | Verified result |
|---|---:|
| Planned UPDATE | 70 |
| CREATE | 0 |
| Missing mapping | 0 |
| Mapping collision | 0 |
| Human-field write | 0 |
| Remote write | 0 |

Local and downloaded remote canonical plan SHA256 both equal:

`af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399`

Additional verification: 70 unique mapped page IDs; zero schema type mismatches; all 10 migration JSON/JSONL artifacts match their local counterparts after JSON parsing, including decision bindings and publication mappings. Notebook Internet remains disabled, bootstrap denies socket connections, and no remote mutation implementation was executed.

This does not approve Phase F. SQL execution, Notion write, scheduler and schema changes were not performed. The 79 data-quality issue entries (70 unstructured values plus 9 ambiguous conditions) and seven proposed schema additions remain findings, not changes applied to production.

Two remote runs exist in total under two separate approvals: version 1 failed before migration; version 2 passed. This latest approval was used for exactly one additional run. Existing private dataset was reused without another snapshot upload.

## Authorized retry — version 2

- User separately approved one additional current NO_WRITE verification after the version-1 failure. No Phase F or mutation scope was granted.
- Fixed bootstrap to support expanded dataset manifest roots and archive fallback, preserving hash checks and denying network connections.
- 67 local tests passed, including execution of the generated notebook against both dataset layouts and comparison with the same local canonical plan.
- Existing private dataset reused; no snapshots re-uploaded. Package ZIP fingerprint unchanged.
- Exactly one additional kernel push issued: version 2 successfully created with Internet/GPU disabled and private metadata.
- Version 2 COMPLETE; downloaded output verification PASS as detailed above. Do not launch any further run without approval.

Scope: one private Kaggle NO_WRITE run, explicitly authorized by the user. No SQL, Notion mutation, scheduler, schema change or Phase F authorization.

- Private dataset: `nguyeble/kf-v161-no-write-baseline`; create acknowledged as private, processing status ready.
- Uploaded ZIP SHA256: `f806aa2b291dff037a10e066fe4d04aae9c11312373fdfb7cf45dcf01bfa71bf`.
- Notebook: `nguyeble/kf-v161-migration-no-write`.
- Exactly one kernel push issued successfully: version 1. Do not rerun without separate authorization.
- Kernel metadata: private; Internet disabled; GPU disabled; no kernel sources or model sources; only the scoped dataset attached.
- Local canonical plan SHA256: `af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399`.
- Status: FAIL — version 1 ended with KernelWorkerStatus.ERROR. Remote verification is not PASS.

The first dataset upload attempt failed locally due to the Kaggle CLI's relative temporary path handling. Retried upload with an absolute path successfully; this was not a notebook run.

## Downloaded evidence and cause

- Downloaded output to `.kaggle-deploy/v161-no-write/remote-v1-output` after the single run ended.
- Output contains `kf-v161-migration-no-write.log`; no migration plan or acceptance report was produced.
- Execution stopped in cell 1 at `assert len(archives) == 1`, immediately after searching `/kaggle/input` for `v161-no-write.zip`.
- Read-only `datasets files` confirms Kaggle expanded the uploaded ZIP: the dataset contains `sha256_manifest.json`, `inputs/*`, `src/kf_pilot/v16/*`, the migration notebook and verification script, not the original ZIP filename.
- Root cause: bootstrap assumes an archive mount instead of supporting Kaggle's expanded dataset layout. It failed before source migration, payload generation or verification.
- Local canonical plan hash remains recorded above. Remote canonical plan hash is unavailable, so equality is NOT VERIFIED.
- Six remote gates are NOT VERIFIED because no migration report was produced. No Notion mutation/SQL/schema/scheduler actions were issued. The failed execution never reached migration.
- Exactly one notebook run was used; no retry was initiated.

## Next action requires approval

Repair the bootstrap to locate the single expanded manifest root (with archive fallback), validate every manifest hash, then authorize one additional NO_WRITE run. No Phase F authorization is implied. The existing private dataset may be reused without re-uploading snapshots.
