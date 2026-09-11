# FINAL_HANDOFF — Vendor 4

conclusion: HANDOFF_READY_OFFLINE
acceptance_claimed: false
code_changed: false
module: VENDOR_4
contract_version: 1.0.0

## Baseline
- Envelope BASELINE.zip SHA256: 47a10d20ab209f8e140cdccb5e45379d60d49f9de6ee202da2344761c701e3e2
- source.zip SHA256 (artifact_subject): 529ef68ebe17424ed66cce1f378a1519b3709b789e91e6f2cd7fe17852065fd4
- source_revision_sha256: bf04692f36c0c0951abee9d9c5b6b6e9e529a0bbaf2cb31332a987e6c959eb46
- contract_sha256: fd3c1b6f1ec5461e7080c538e1c332d7af3098db32edd1565e1ae16933f951a8
- Patches this closeout: none (code frozen)

## Gates
| Gate | Result | Evidence |
|---|---|---|
| Offline pytest suite | PASS 55/55 | closeout kit evidence/v4.xml, v4-pytest.txt; baseline evidence/junit.xml |
| Schema drift reject (expected B / provider A) | PASS | evidence/v4-repro.txt CHANGES_REQUIRED/SCHEMA_DRIFT |
| Positive expected B / provider B / target B | PASS | tests/test_preflight_r5.py::test_expected_b_provider_b_target_b_pass |
| Missing expected pin not VERIFIED | PASS | test_missing_expected_pin_blocked |
| Truncated relation reject | PASS | R4 tests kept |
| Process restart | PASS | tests/test_process_restart.py |
| G1 clean venv install | BLOCKED_ENVIRONMENT | ensurepip missing; reviewer used existing env |
| G7 live Notion/staging | NOT_RUN | no authorized token/opt-in |
| Docker | NOT_RUN | not executed |
| Production | OUT_OF_SCOPE | |

Mock vs actual: all PASS above are mock/offline. Live/actual not claimed.

## Tests
Reviewer + baseline: 55 passed, 0 failed, 0 skipped. Counts must match JUnit in evidence/.

## Known limitations (unchanged)
- No owner-pinned expected_schema for the four THBISON staging data sources
- Ranking is rule baseline
- Signed URLs are sim://
- In-process cache except durable upload ledger on V4_DATA_DIR

## Internal integration conditions
See INTERNAL_TAKEOVER.md. Offline handoff does not mean live or production ready.
