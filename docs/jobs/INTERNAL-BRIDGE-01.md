# INTERNAL-BRIDGE-01

JOB_ID=INTERNAL-BRIDGE-01
ISSUE=https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/10
BRANCH=internal/bridge-01
BASE=b6b61ac6905b94a52a1289846117fc61e7c6e3a8
J3_CODE_IN_FREEZE=f8985448b84f309ad80b89843008d3608426337f
J2_ENV_COMMIT=8b197d67f70f6db614a8aefdda7b84f0d4009827
CONTRACTOR=trunghungvtcn/pipeline-lab-contractor-m1-m5@afac091e60bb6c8a0f0630964e43f5e80951267c
MODE=LOCAL_SHADOW / TEST_ONLY
acceptance_claimed=false
real_data_pass=false

Internal takeover of remaining contractor-bridge defects. Does **not** reopen vendor J3 or F1–F7. Vendor files under `docs/jobs/J3-*` are unchanged. Contractor public API is out of scope.

## Pins (split; never HASH_VERIFIED here)

| Role | Field | Value | Status |
|---|---|---|---|
| Code / inventory commit | `j1_commit_sha` | `b9e291fb84ddf99a6e6dd662ae122f39326f4d41` | published on issue #3 (inventory HEAD). Later J1 final `6fae4c4` is on another branch and is not rewritten into vendor mapping. |
| Input hash | `j1_input_hash` | published inventory digest `318a7db871bb056e321d75d18063b9267ece121d7a36f604aaca08ca167f7c89` | **PUBLISHED_UNVERIFIED**. Not HASH_VERIFIED of the private corpus. Live content hash `86165e10…` on J1 HEAD is also not upgraded. |
| Environment commit | `j2_commit_sha` | `8b197d67f70f6db614a8aefdda7b84f0d4009827` | J2 is environment evidence, not corpus. Vendor `mapping.J2_PUBLISHED` remains the historical `5e616191…` record. |
| Environment hash | `j2_input_hash` | JUnit sha256 `fccd4eeab5f897e882937d7cd36081e09786a773df237981f4c57d3240223962` (issue #4) | ENVIRONMENT_UNVERIFIED. Not corpus. |
| Contractor | — | `afac091e60bb6c8a0f0630964e43f5e80951267c` | public packages only |

Fixtures in tests are `TEST_ONLY` / `SYNTHETIC`. Synthetic PASS is recorded as `synthetic_pass` and is **not** `real_data_pass`. Missing real data stays BLOCKED_INPUT. Hashes are not invented.

## Defects closed on this job

| ID | Fix |
|---|---|
| B1 | Missing/malformed pins return HUMAN_HOLD BLOCKED_INPUT **before** freeze, ledger admit, or project. |
| B2 | `DUPLICATE_NOOP` only when ledger `state=SUCCEEDED`, `projection_status=APPLIED` (`JobLedger.mark_projected` public API), and durable `shadow-receipt.json` matches job/fingerprint/digest. Otherwise safe resume of projection, or `RECONCILE_REQUIRED`. Contractor schema not patched. |
| B3 | Allow-list is `type(transport) is FakeTransport`. `LOCAL_SHADOW_ALLOWED` is ignored. Subclasses and self-flagged objects are rejected with zero transport calls. Check runs before `Projector.project`. |
| B4 | Request digest binds commit SHA, environment SHA, and input hash separately. J2 labeled `environment`. `j1_input_verified` stays false. |

## Run

```bash
git clone https://github.com/trunghungvtcn/pipeline-lab-contractor-m1-m5.git contractor
git -C contractor checkout afac091e60bb6c8a0f0630964e43f5e80951267c
export CONTRACTOR_ROOT="$PWD/contractor"
export PYTHONPATH="$CONTRACTOR_ROOT/m1_locator/src:$CONTRACTOR_ROOT/m2_asset_store/src:$CONTRACTOR_ROOT/m3_job_ledger/src:$CONTRACTOR_ROOT/m4_notion_projection/src:$PWD/src"
python -m pytest tests/jobs/test_internal_bridge_01.py tests/jobs/test_internal_bridge_01_contractor.py tests/jobs/test_j3_mapping.py tests/jobs/test_j3_adapter_shadow.py tests/jobs/test_j3_holds.py tests/jobs/test_j3_contractor_required.py -q --junitxml=docs/jobs/INTERNAL-BRIDGE-01-junit.xml
```

Missing CONTRACTOR_ROOT / packages → command fails (not skip-pass).

Vendor J3 tests stay in the command to keep the three contractor PASS gates.

## Out of scope

merge, deploy, scheduler, live Notion, paid models, contractor edits, extra GitHub Release, vendor F1–F7, ACCEPTED.
