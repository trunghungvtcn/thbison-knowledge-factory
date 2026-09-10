# J2 PROMPT — final remediation

JOB_ID=J2
MAILBOX=https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/4
PUBLISHED_HEAD=8b197d67f70f6db614a8aefdda7b84f0d4009827
PR=https://github.com/trunghungvtcn/thbison-knowledge-factory/pull/8
SOURCE=https://github.com/trunghungvtcn/thbison-knowledge-factory/commit/8b197d67f70f6db614a8aefdda7b84f0d4009827
CORE=3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b

This kit **needs GitHub**. It is not offline-complete.

J2 is **PUBLISHED**, not UNPUBLISHED. HEAD was read from issue #4 on 2026-09-10:

- issue body `HEAD_SHA=8b197d67f70f6db614a8aefdda7b84f0d4009827`
- draft PR #8 head, same SHA
- branch `jobs/j2-core-verification-20260910`, same SHA

Earlier SHA `5e6161914f519403059ce13a1568d58ac7162f28` is a parent on the same PR (before `j2_verify_payload.py`). Do not treat it as current HEAD. Do not mark J2 UNPUBLISHED.

Read `COMMON_RULES.md` and `BASELINES.json` first.

## Allowed trees

- environment / runner config for source-only verification
- `.github/workflows/verify.yml`
- `scripts/jobs/j2_*`
- `docs/jobs/J2*`

Do not edit `tests/*.py`. Do not edit J1 manifests. Do not edit contractor CI.

## Current state at PUBLISHED_HEAD

`scripts/jobs/j2_source_only_pytest.py` already deselects six asset-bound nodeids when the asset is absent, writes sidecar JSON `not_run[]` with `nodeid`, `status=NOT_RUN`, `asset`, `reason`, and annotates JUnit with `head_sha`. `scripts/jobs/j2_verify_payload.py` wraps recovered-tree payload checks and exempts only `scripts/jobs/j2_*` and `docs/jobs/J2*`.

Known remaining gaps against this final scope:

1. Deselected rows use `NOT_RUN` and field `asset`. Acceptance requires every deselected test to carry **nodeid + missing input + status `BLOCKED_INPUT` or `NOT_RUN`** in the receipt. Rename/add the missing-input field if needed; keep `NOT_RUN` where the suite was intentionally not executed; use `BLOCKED_INPUT` when the reason is absent required input.
2. Do not let docs, CI summary, or issue comments say **full-suite PASS** for a source-only / deselected run. `mode=source-only` must stay visible. Counts must show ran vs deselected.
3. HEAD, exact command, exit code, JUnit path, and tests-actually-run must be published on issue #4 for the SHA under review.
4. Source-only suite **may** be split from a suite that needs private/gitignored data. Do not publish that data.

## Required final fix

1. Source-only suite may be split from suites that need private / gitignored assets.
2. Every deselected test must appear in the receipt with: nodeid, missing input, status `BLOCKED_INPUT` or `NOT_RUN`.
3. Do not claim full-suite PASS from a subset.
4. Publish HEAD (`8b197d67…` or a later SHA on the same job branch), exact command, exit code, JUnit, and the number of tests actually executed.
5. Do not change algorithms. Do not change contractor CI.

## Out of scope

Contractor repo, algorithm changes, merge, deploy, corpus publication, rewriting J1 inventory, expanding the six-nodeid list by shipping assets to GitHub.

## Done when

READY_FOR_REVIEW on issue #4. `acceptance_claimed=false`.
