# J3 PROMPT — final remediation

JOB_ID=J3
MAILBOX=https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/2
POINTER=https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/5
REVIEWED_SHA=9a7d09375bf242f3cf89b9e2d556192a12e8b830
PR=https://github.com/trunghungvtcn/thbison-knowledge-factory/pull/6
CORE=3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b
CONTRACTOR=afac091e60bb6c8a0f0630964e43f5e80951267c
J1_REVIEWED=b9e291fb84ddf99a6e6dd662ae122f39326f4d41
J2_PUBLISHED=5e6161914f519403059ce13a1568d58ac7162f28

This kit is a GitHub-required guidance pack. It is not offline-complete.
Issue #5 remains a pointer to #2. Do not delete #5 history.

## Allowed trees

- `src/kf_pilot/contractor_bridge/`
- `tests/jobs/test_j3_*`
- `docs/jobs/J3*`

## Required final fix

1. Reject a non-allowed transport **before** `Projector.project`. Do not infer safety from class name prefix `Fake` or from a `calls` attribute.
2. Check envelopes for `reserve_budget`, `record_attempt`, `finalize`, and `project`. Any of those in error must not return `LOCAL_SHADOW_COMPLETE`.
3. Replay must inspect current job state first. `IDEMPOTENT_HIT` is not automatically a completed success.
4. Check J1/J2 pins before execute. Split **commit SHA** from **input hash**. Bind both into request digest and receipt. Do not treat "looks like a SHA" as verified.
5. Acceptance command must fail closed when contractor packages are missing. Do not `importorskip` then declare PASS.
6. Edit only the J3 adapter namespace and its tests/docs.

## Out of scope

Contractor internals, live Notion, merge, deploy, scheduler, paid models.
