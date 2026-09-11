# Vendor 6 — FINAL HANDOFF

status: HANDOFF_WITH_BLOCKERS  
acceptance_claimed: false  
code_changed: false  
round: FINAL (docs only; no R3)

## Source freeze
- Baseline: reviewer `input/BASELINE-R2.zip` = envelope SHA `2e4b1e28863428b9d7d2c6044db43a4af8c7167d0be6f9799adfdf2ddd7ebbf2`
- `source.zip` copied byte-identical from that baseline.
- source.zip SHA256: `a8c5267044ee3aacce1f9729349c8ac789ccc93ed43cbe7a72f90e78735188a6`
- SOURCE_REVISION.txt SHA256: `9022947278ceb2600ee5a7c4743b11a160076e227581b8b3e4b3f914e7b0cb8a`
- contract 1.0.0 pin: `fd3c1b6f1ec5461e7080c538e1c332d7af3098db32edd1565e1ae16933f951a8`

No source, fixture, or test file was modified in this package. Tests were not re-run to inflate PASS.

## Issue closeout (reviewer verdict)
| ID | Status | Note |
|---|---|---|
| V6-R2-01 | CLOSED | Registry dispatch; Trap raises ACTUAL_ADAPTER_WAS_CALLED:plan |
| V6-R2-02 | CLOSED | Receipt always validated; no weirdField bypass |
| V6-R2-03 | PARTIAL/OPEN | Fake protocol incomplete vs staging verification. See INTERNAL_TAKEOVER.md |

## Layer split (do not collapse)
| Layer | Result | Meaning |
|---|---|---|
| Fake Notion protocol (FakeNotionTransport) | mock tests only | not live staging, verified=false |
| Spy / fake-HTTP adapter dispatch | mock tests only | verified_component=false; not a deployed vendor |
| Actual V1–V5 processes | NOT_RUN | INT-26 skip; no pinned accepted binaries in this kit |
| Live staging | BLOCKED_ACCESS | no out-of-band token; no live call |
| Paired benchmark | NOT_RUN | INT-27 skip |
| G1 clean install | BLOCKED_ENVIRONMENT | ensurepip missing; reviewer used preinstalled env |

71 PASS does not close actual integration, live staging, G1, or R2-03.

Internal team owns remaining preflight work and any later integration job. This handoff does not claim acceptance.
