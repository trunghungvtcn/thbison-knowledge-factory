# V16.4 Semantic Remediation Execution Report

Run date: 2026-09-05  
Mode: `LOCAL / NO_WRITE`  
Authoritative artifacts: `v164/artifacts/final-003`  
Independent replay: `v164/artifacts/replay-003`

## Final status

`V164_SEMANTIC_PIPELINE_PASS / PHASE_F_NOT_AUTHORIZED`

This result is a local semantic-analysis pass only. It is not Phase F approval and
does not authorize a Notion/Kaggle/SQL/scheduler/schema mutation.

## Verification results

| Check | Measured result |
|---|---:|
| V16.4 reference/integration tests | 60/60 PASS |
| Full repository tests | 242/242 PASS |
| V16.3 source-binding gate | PASS — 79 issues, 5 candidates, 0 accepted |
| V16.2 remediation-ledger gate | PASS — 79 total, 0 RESOLVED, 11 HOLD, 68 NEEDS_REVIEW |
| V16.2 Phase F readiness gate | PASS — 0 canary, `authorized_to_execute=false` |
| V16.4 independent re-extraction/recomputation gate | PASS |
| Final/replay equality | `BYTE_AND_HASH_EQUALITY_PASS` — 15 files |

V16.1 canonical baseline before and after:

`af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399`

## Actual repository data

| Metric | Count |
|---|---:|
| Canonical records | 70 |
| Accounted issues | 79 |
| `OBJECT_VALUE_UNSTRUCTURED` | 70 |
| `CONDITION_CONNECTIVE_AMBIGUOUS` | 9 |
| V16.3 candidates reverified from raw bytes | 5 |
| Valid V16.4 semantic proposals | 2 |
| Blocked candidates | 3 |
| Independent adjudications | 0 |
| Accepted derivations | 0 |
| V16.2-compatible adapter inputs | 0 |
| Resolved by this run | 0 |
| Production/canary eligible | 0 / 0 |

The two valid proposals are the conditional inspection intervals of one year and
three years. Their raw PDF hash, PyMuPDF extractor version, exact page locator,
character offsets, quantity/unit spans, full semantic payload, applicability,
jurisdiction, unresolved condition AST, exception AST, target version and proposal
hash were preserved. Both preview as `V162_CONTRACT_INCOMPATIBLE` because V16.2
still requires the whole original object literal and does not accept prose-to-scalar.

The three prohibition candidates remain blocked with
`AUTHORITATIVE_VOCABULARY_MISSING`. V16.4 did not create an enum vocabulary from
the source wording and did not treat a proposal as an authority.

All nine ambiguous connective issues keep their stable issue identity and remain
`HOLD`/`NEEDS_REVIEW`; no AND/OR/NOT connective was inferred.

## Safety and mutation counters

| Counter | Value |
|---|---:|
| Production writes | 0 |
| Human-field writes | 0 |
| CREATE operations | 0 |
| SQL executions | 0 |
| Schema mutations | 0 |
| Scheduler actions | 0 |

The empty V16.2 replay preserved all 79 unresolved issues and the 70 mappings.
`Decision` and `Reviewer Note` were captured read-only in the audit snapshot.
The Phase F canary is empty and explicitly has `authorized_to_execute: false`.

## Artifact integrity

SHA256 of `final-003/artifact_hashes.json`:

`d154b411445d239a3a4167cf0b52e0158dffe6f49946baa40fe476cd38148aaf`

The independent gate reloaded the V16.1/V16.2/V16.3 state, checked upstream
binding hashes and manifests, re-extracted the pinned PDF/HTML raw bytes, recomputed
V16.4 outputs, and compared final/replay artifacts byte-for-byte.

## Required next inputs

Progress beyond this point requires separate authoritative inputs, not another
automatic run:

1. An approved, independently versioned vocabulary for the three prohibition
   meanings, with authority reference and exact source literals.
2. Independent semantic adjudications for the two interval proposals, bound to
   proposal hash, issue/entity/base/target version, reviewer identity/scope/time,
   rationale and all review checks.
3. If accepted derivations should enter V16.2, a separately reviewed versioned
   extension contract for evidence-derived prose-to-scalar values. The existing
   whole-literal gate was not relaxed.

Even after those inputs, Phase F still requires a separate explicit approval.
