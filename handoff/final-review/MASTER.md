# MASTER — J1–J3 final remediation handoff

status: READY_FOR_REVIEW
acceptance_claimed: false
kind: GitHub guidance pack (not offline-complete)
code_changed: false
date: 2026-09-10

This pack publishes the **final fix plan and prompts** for J1, J2, and J3.
It does **not** implement the fixes. It does **not** claim ACCEPTED.
It does **not** claim offline-complete.

## Baselines

| Pin | SHA | Evidence |
|---|---|---|
| Core / working baseline | `3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b` | PR #1 head `fix/migration-architecture-alignment` |
| J1 reviewed source | `b9e291fb84ddf99a6e6dd662ae122f39326f4d41` | draft PR #7 |
| J2 published HEAD | `5e6161914f519403059ce13a1568d58ac7162f28` | issue #4 body + draft PR #8 |
| J3 reviewed source | `9a7d09375bf242f3cf89b9e2d556192a12e8b830` | draft PR #6 |
| Contractor public API | `afac091e60bb6c8a0f0630964e43f5e80951267c` | `trunghungvtcn/pipeline-lab-contractor-m1-m5` |

J2 is **published**, not UNPUBLISHED. Read from issue #4 on 2026-09-10.

## Issues and PRs

- J1 mailbox: https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/3
- J2 mailbox: https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/4
- J3 mailbox (primary): https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/2
- J3 downstream pointer: https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/5 — keep history; route work to #2
- J1 PR: https://github.com/trunghungvtcn/thbison-knowledge-factory/pull/7
- J2 PR: https://github.com/trunghungvtcn/thbison-knowledge-factory/pull/8
- J3 PR: https://github.com/trunghungvtcn/thbison-knowledge-factory/pull/6
- Core PR: https://github.com/trunghungvtcn/thbison-knowledge-factory/pull/1

## Guidance packs (one ZIP per job)

Each ZIP is a **prompt kit that needs GitHub**. It is not an executable remediation and is not offline-complete.

Download from this GitHub Release and verify:

```text
sha256sum -c SHA256SUMS.txt
```

```text
fd611f749e9102feb76ea8e06eb0d617d18fae6713d60e82f027e5bc1bb18d21  J1-final-fix.zip
c3dd40e82ca7d37c6a356e0bfb613d8cae73ae11469a39e1ba875a5a6c0e6705  J2-final-fix.zip
c0fea0246dadcbd458b4fed75635a466d7ac8421a5980df31aafeeb2e7af7364  J3-final-fix.zip
```

Unpacked sources: `handoff/final-review/packages/J*-final-fix/`. Binary ZIPs are gitignored.

Tree on this branch: `handoff/final-review/`
Tag: `handoff-j1-j3-final-20260910`

## Coordination

- One implementation pass + one reviewer pass per job.
- Do not start other jobs from out-of-scope comments.
- Do not merge, deploy, enable scheduler, or write live Notion.
- Do not upload private corpus, real snapshots, tokens, or secrets.
- Keep the three contractor PASS gates untouched.
- READY_FOR_REVIEW is not ACCEPTED.

## Limits

- J1 scope: `scripts/jobs/j1_*`, `tests/jobs/test_j1_*`, `docs/jobs/J1*`
- J2 scope: environment config, `.github/workflows/verify.yml`, `scripts/jobs/j2_*`, `docs/jobs/J2*`
- J3 scope: `src/kf_pilot/contractor_bridge/`, `tests/jobs/test_j3_*`, `docs/jobs/J3*`
