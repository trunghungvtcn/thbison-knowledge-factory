# J3 PROMPT — final remediation

JOB_ID=J3
MAILBOX=https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/2
POINTER=https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/5
REVIEWED_SHA=9a7d09375bf242f3cf89b9e2d556192a12e8b830
PR=https://github.com/trunghungvtcn/thbison-knowledge-factory/pull/6
SOURCE=https://github.com/trunghungvtcn/thbison-knowledge-factory/commit/9a7d09375bf242f3cf89b9e2d556192a12e8b830
CORE=3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b
CONTRACTOR=afac091e60bb6c8a0f0630964e43f5e80951267c
J1_REVIEWED=b9e291fb84ddf99a6e6dd662ae122f39326f4d41
J2_PUBLISHED=8b197d67f70f6db614a8aefdda7b84f0d4009827

This kit **needs GitHub**. It is not offline-complete.
Issue #5 remains a pointer to #2. Do not delete #5 history. Do not execute the fix from #5 comments.

Read `COMMON_RULES.md` and `BASELINES.json` first.

## Allowed trees

- `src/kf_pilot/contractor_bridge/`
- `tests/jobs/test_j3_*`
- `docs/jobs/J3*`

## Current defects at REVIEWED_SHA

In `src/kf_pilot/contractor_bridge/adapter.py` @ `9a7d093`:

1. **Transport check is after project, and is name-based.** `Projector.project(...)` runs, then live transport is inferred from `type(self.transport).__name__.startswith("Fake")` and `getattr(self.transport, "calls", [])`. Disallowed transport must be rejected **before** `Projector.project`. Do not use class-name prefix `Fake` or a `calls` attribute as the allow-list.
2. **Failed ledger/project envelopes can still complete.** `reserve_budget`, `record_attempt`, and `finalize` results are stored on `envelopes` but not fail-closed. `LOCAL_SHADOW_COMPLETE` is then assigned if pin-holds are empty. Any of those operations in error, and any failed `project`, must not return `LOCAL_SHADOW_COMPLETE`.
3. **Replay treats IDEMPOTENT_HIT as done.** On `admit.reason_code == "IDEMPOTENT_HIT"` the adapter returns `DUPLICATE_NOOP` without reading current job state (`ledger.get`). `IDEMPOTENT_HIT` is not automatically a completed success.
4. **Commit SHA and input hash are collapsed.** Constructor takes `j1_input_sha` / `j2_env_sha` and only checks truthiness. `_request_digest` binds contract fingerprint + snapshot hash + baselines, not the J1/J2 commit SHA and input hash as separate fields. A hex string must not be treated as verified.
5. **Acceptance tests `importorskip` contractor packages.** `tests/jobs/test_j3_adapter_shadow.py` and `tests/jobs/test_j3_holds.py` call `pytest.importorskip`. Missing contractor dependency then looks like PASS (skipped). The acceptance command must fail closed.

## Required final fix

1. Reject a non-allowed transport **before** `Projector.project`. Allow-list by explicit injected type / registry (for example identity with contractor `FakeTransport`), not by name prefix and not by presence of `calls`.
2. Inspect results of `reserve_budget`, `record_attempt`, `finalize`, and `project`. Any of those in error → not `LOCAL_SHADOW_COMPLETE`.
3. Replay must inspect job state first. `IDEMPOTENT_HIT` + non-terminal job is not complete.
4. Check J1/J2 pins before execute. Split **commit SHA** from **input hash** for both J1 and J2. Bind those four values into request digest and receipt. Known published values (do not invent others):
   - J1 commit SHA = `b9e291fb84ddf99a6e6dd662ae122f39326f4d41`
   - J1 inventory content hash (published, not a private-corpus verify) = `318a7db871bb056e321d75d18063b9267ece121d7a36f604aaca08ca167f7c89`
   - J2 commit SHA = `8b197d67f70f6db614a8aefdda7b84f0d4009827`
   - J2 has no separate published env/input hash on issue #4; if the adapter requires one, it is `BLOCKED_INPUT` until J2 publishes it. Do not mint a stand-in.
5. Acceptance command must report missing contractor dependency with exit ≠ 0. Do not `importorskip` then declare PASS.
6. Edit only the J3 adapter namespace and its tests/docs.

## Out of scope

Contractor internals, live Notion, merge, deploy, scheduler, paid models, J1/J2 code trees.

## Done when

READY_FOR_REVIEW on issue #2. Pointer comment only on issue #5. `acceptance_claimed=false`.
