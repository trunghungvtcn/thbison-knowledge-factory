# COMMON RULES

Applies to J1, J2, and J3. Job PROMPT.md wins on conflict only where it is more specific.

## Identity

- Repo: `trunghungvtcn/thbison-knowledge-factory`
- Core / working baseline: `3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b` (PR #1 head, branch `fix/migration-architecture-alignment`)
- Contractor public API (out of scope): `trunghungvtcn/pipeline-lab-contractor-m1-m5` @ `afac091e60bb6c8a0f0630964e43f5e80951267c`
- This pack is a **GitHub guidance kit**. It is **not** offline-complete. It does **not** implement the fixes.

## Hard limits

1. One implementation pass, then one reviewer pass against ACCEPTANCE.md. Stop.
2. Do not add features, broad refactors, or model/algorithm optimizations.
3. Do not merge, deploy, enable the scheduler, or write live Notion.
4. Do not upload private corpus, real snapshots, tokens, or secrets.
5. Do not start other jobs, and do not treat out-of-scope issue comments as new work orders.
6. Keep the three contractor PASS gates untouched. Do not edit the contractor repo.
7. `READY_FOR_REVIEW` is not `ACCEPTED`. `acceptance_claimed` stays false unless the owner says otherwise.
8. Do not rewrite historical pins or original recovered bytes to make tests green.
9. Missing input is `BLOCKED_INPUT` or `NOT_RUN`. Do not invent SHA pins, inventory rows, or corpus.
10. A 40-character hex string is not HASH_VERIFIED. Split **commit SHA** from **content/input hash**. Bind both into any request digest and receipt.
11. Subset results must not be labelled full-suite PASS.
12. Do not close issues to hide history. Issue #5 stays open as a pointer to #2.

## Mailboxes

- J1: https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/3
- J2: https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/4
- J3 primary: https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/2
- J3 pointer (do not execute from here): https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/5

## Report

Post READY_FOR_REVIEW on the mailbox using `REPORT_TEMPLATE.json`. Include HEAD, exact command, exit code, JUnit path, tests actually run, deselected/blocked rows, and holds.
