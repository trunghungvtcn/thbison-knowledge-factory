# J3 INTERNAL TAKEOVER — frozen defect list

JOB_ID=J3
STATUS=READY_FOR_REVIEW
acceptance_claimed=false
conclusion: HANDOFF_READY_OFFLINE
code_changed_this_note: false
HEAD_SHA=f8985448b84f309ad80b89843008d3608426337f
REVIEWED_BEFORE_REMEDIATE=9a7d09375bf242f3cf89b9e2d556192a12e8b830
PR=https://github.com/trunghungvtcn/thbison-knowledge-factory/pull/6
MAILBOX=https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/2
DATE=2026-09-10

This list is **frozen**. Do not open new feature requests from it.
Owner/internal integration owns each item. Vendor J3 scope on this branch stops here.

## Frozen items

| ID | Status | Item | Owner |
|---|---|---|---|
| J3-F1 | BLOCKED_INPUT | J1 inventory **content hash** unpublished. `j1_input_verified` stays false. Synthetic `1`*64 in tests is not HASH_VERIFIED. | J1 / owner |
| J3-F2 | BLOCKED_INPUT | J2 asset/env **content hash** unpublished. `j2_input_verified` stays false. Synthetic `2`*64 in tests is not HASH_VERIFIED. J2 **commit** `5e6161914f519403059ce13a1568d58ac7162f28` is published (issue #4). | J2 / owner |
| J3-F3 | BLOCKED_ENVIRONMENT | Acceptance command needs `CONTRACTOR_ROOT` + four contractor `src/` trees at `afac091e60bb6c8a0f0630964e43f5e80951267c`. Clean-venv lock install is not certified on this packager. | internal |
| J3-F4 | NOT_RUN | Live staging / real Notion / paid model. LOCAL_SHADOW + FakeTransport only. | out of scope |
| J3-F5 | BLOCKED_OWNER_DECISION | JobLedger has no columns for factory `code_commit` / dataset snapshot; pins live on receipt only. | reviewer |
| J3-F6 | NOT_CLAIMED | GitHub Releases tag `handoff-j1-j3-final-20260910` was not created (no Releases API in packager session). Guidance pack is PR #9 + tree `handoff/final-review/`. | internal |
| J3-F7 | NOTE | Injected transport must set `LOCAL_SHADOW_ALLOWED is True` (`mark_allowed`). Default adapter-built FakeTransport is marked. Class name `Fake*` is not an allow-list. | documented |

## Explicitly closed on this HEAD (do not reopen as features)

- Allow-list before `Projector.project`
- Envelope checks on reserve / attempt / finalize / project
- Replay reads ledger state
- Commit SHA vs input hash split + digest binding
- No `importorskip` PASS

## Rules for internal takeover

1. Do not treat READY_FOR_REVIEW as ACCEPTED.
2. Do not rewrite historical pins to go green.
3. Do not merge, deploy, enable scheduler, or write live Notion from this job.
4. Do not expand J3 into contractor internals or CI.
5. New work requires a new JOB_ID, not an amendment of this list.
