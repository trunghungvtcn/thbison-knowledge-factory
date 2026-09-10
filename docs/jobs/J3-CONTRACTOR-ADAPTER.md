# J3 LOCAL_SHADOW contractor adapter

JOB_ID=J3
BRANCH=jobs/j3-contractor-adapter-20260910
BASE_SHA=3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b
CONTRACTOR_BASELINE=afac091e60bb6c8a0f0630964e43f5e80951267c
MODE=LOCAL_SHADOW
acceptance_claimed=false

## Scope

Only these trees:

- `src/kf_pilot/contractor_bridge/`
- `tests/jobs/test_j3_*`
- `docs/jobs/J3*`

Contractor implementation is not patched. Internals are not faked.

## Public API used

| Package | Symbols |
|---|---|
| grok_locator | LocatorResolver.validate, LocatorResolver.resolve, LocatorProfile |
| grok_asset_store | AssetStore.freeze, AssetStore.verify_manifest, AssetStore.is_published, SourceRef, DictReader |
| grok_job_ledger | JobLedger.admit, claim, record_attempt, finalize, reserve_budget, get, history |
| grok_notion_projection | Projector.project, FakeTransport |

See `src/kf_pilot/contractor_bridge/mapping.py`.

## Behaviour

1. Refuse any `RunContract.mode` other than `TEST_ONLY`.
2. Verify snapshot SHA256 against `input_manifest_sha256`.
3. Resolve locator from a work-root relative path (no symlink follow; contractor resolver).
4. Freeze snapshot into a local CAS directory.
5. Admit the contract fingerprint on a local SQLite ledger.
6. Claim, reserve attempt budget, finalize `SUCCEEDED`.
7. Project status through `FakeTransport` only. No live Notion, no scheduler, no paid model.
8. Replay of the same fingerprint returns `IDEMPOTENT_HIT` / `DUPLICATE_NOOP`.
9. Missing J1 input SHA or J2 environment SHA is `HUMAN_HOLD` + `BLOCKED_INPUT`. Evidence is not invented.

## Run

```bash
git clone https://github.com/trunghungvtcn/pipeline-lab-contractor-m1-m5.git contractor
git -C contractor checkout afac091e60bb6c8a0f0630964e43f5e80951267c
export CONTRACTOR_ROOT="$PWD/contractor"
export PYTHONPATH="\
$CONTRACTOR_ROOT/m1_locator/src:\
$CONTRACTOR_ROOT/m2_asset_store/src:\
$CONTRACTOR_ROOT/m3_job_ledger/src:\
$CONTRACTOR_ROOT/m4_notion_projection/src:\
$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
python -m pytest tests/jobs/test_j3_mapping.py tests/jobs/test_j3_adapter_shadow.py tests/jobs/test_j3_holds.py -q --junitxml=docs/jobs/J3-junit.xml
```

J1 / J2 commit SHAs were not published on issues at adapter start. Pass them into `LocalShadowAdapter(j1_input_sha=..., j2_env_sha=...)` when those jobs land.

## Out of scope

- merge, deploy, scheduler
- live Notion writes
- paid model calls
- credentials or private corpus on GitHub
- editing contractor packages
