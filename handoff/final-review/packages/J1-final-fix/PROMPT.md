# J1 PROMPT — final remediation

JOB_ID=J1
MAILBOX=https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/3
REVIEWED_SHA=b9e291fb84ddf99a6e6dd662ae122f39326f4d41
PR=https://github.com/trunghungvtcn/thbison-knowledge-factory/pull/7
SOURCE=https://github.com/trunghungvtcn/thbison-knowledge-factory/commit/b9e291fb84ddf99a6e6dd662ae122f39326f4d41
CORE=3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b

This kit **needs GitHub**. It is not offline-complete. Do not implement anything outside the allowed trees.

Read `COMMON_RULES.md` and `BASELINES.json` first.

## Allowed trees

- `scripts/jobs/j1_*`
- `tests/jobs/test_j1_*`
- `docs/jobs/J1*`

Fork from reviewed SHA `b9e291fb84ddf99a6e6dd662ae122f39326f4d41` (or from Core `3f1f125` and replay only J1 files). Do not cherry-pick J2/J3.

## Current defects at REVIEWED_SHA

Observed in `scripts/jobs/j1_input_audit.py` @ `b9e291f`:

1. **Exit code.** `main()` always `return 0` after writing the inventory, even when rows are `MISSING` / `MISSING_EXTERNAL` / `HASH_MISMATCH`. There is no strict mode.
2. **PRESENT vs HASH_VERIFIED.** Status `OK` means "file exists" for some runtime rows (no expected digest) and "exists and digest matches" for locator/GitHub rows. Those must not share a label.
3. **Three hashes are not published separately.** The report has `base_sha` (git HEAD) and `inventory_sha256` (canonical report fingerprint). It does not publish the auditor **tool SHA**, and it does not document how to reproduce each hash on the exact bytes.

Do **not** "fix" this by rewriting `manifests/migration_assets.json`, nested historical pins, recovered artifacts, or `farming_input`. Nested HASH_MISMATCH rows are evidence, not bugs to paint over.

## Required final fix

1. Add a **strict** mode (flag such as `--strict`). In strict mode, missing path or hash mismatch → process exit code **≠ 0**. Keep the existing inventory/report mode that lists rows and can still exit 0.
2. Distinguish **PRESENT** (path exists on disk) from **HASH_VERIFIED** (bytes match the published digest on that exact file). A present file with no expected digest is PRESENT, never HASH_VERIFIED. A matching digest is HASH_VERIFIED (and may also be PRESENT).
3. Separate and publish:
   - **audited source SHA** = git commit of the inventory code (`git rev-parse HEAD`)
   - **tool SHA** = SHA256 of the auditor script bytes (`scripts/jobs/j1_input_audit.py`) or its git blob (`git hash-object`)
   - **inventory content hash** = hash of the canonical inventory document (existing `fingerprint()` / `inventory_sha256` is acceptable if the recipe is written down)
   Publish the exact reproduction command for each, against the same bytes.
4. Do not edit historical pins or original recovered data to make tests green.
5. Tests cover only the three rules above. If an input is absent, report it honestly (`BLOCKED_INPUT` / `MISSING` / `MISSING_EXTERNAL`). Do not fabricate rows.

## Tests

Extend `tests/jobs/test_j1_input_audit.py` only. Suggested cases:

- inventory mode: missing fixture still produces a report; watched recovered files stay byte-identical
- strict mode: missing required path → exit ≠ 0
- strict mode: hash mismatch → exit ≠ 0
- a present file with no expected digest is labelled PRESENT, not HASH_VERIFIED
- a matching digest is HASH_VERIFIED
- report contains the three hashes plus reproduction text

Do not assert that private parquet / custody zips / `manual_decisions.csv` are present.

## Out of scope

Merge, deploy, scheduler, Notion writes, paid models, contractor repo, private corpus upload, J2/J3 trees.

## Done when

READY_FOR_REVIEW on issue #3 with HEAD, command, exit code, JUnit, and the three hashes. `acceptance_claimed=false`.
