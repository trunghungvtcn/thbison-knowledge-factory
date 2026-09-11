# V16.3 Evidence Binding execution report

**Final status: `V163_BINDING_PIPELINE_PASS / PHASE_F_NOT_AUTHORIZED`**

V16.3 has been implemented locally in the separate `kf_pilot.v163_evidence` namespace. It builds evidence-addressed review work, verifies source bytes and exact locators, creates conservative binding proposals, validates independent human adjudications, and feeds only accepted compatible bindings back through the existing V16.2 path. It has no production mutation transport.

## Required execution results

| Field | Result |
| --- | --- |
| Full tests | 182/182 PASS in the final run |
| V16.1 baseline before | `af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399` |
| V16.1 baseline after | `af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399` |
| Authoritative issues | 79: 70 OBJECT_VALUE_UNSTRUCTURED; 9 CONDITION_CONNECTIVE_AMBIGUOUS |
| Source bytes available/unavailable | 79 / 0 |
| Issues with exact relevant spans | 70; the 9 connective issues remain without a connective-proving span |
| Binding candidates | 5 total: two explicit inspection intervals and three explicit prohibition statements |
| Reviewer ACCEPT / REJECT / HOLD / NEEDS_MORE_EVIDENCE | 0 / 0 / 0 / 0 |
| Awaiting adjudication | 79 work items; five have candidates, the others need stronger evidence |
| Accepted bindings | 0 |
| Post-V16.2 RESOLVED / HOLD / NEEDS_REVIEW | 0 / 11 / 68 |
| Post-reconciliation unresolved | 79 |
| Eligible production records | 0 |
| Eligible canary records | 0; `authorized_to_execute=false` |
| Mapping collisions / missing mappings | 0 / 0 |
| Production writes | 0 |
| Human-field writes | 0 |
| CREATE operations | 0 |
| SQL executions | 0 |
| Scheduler actions | 0 |
| Schema mutations | 0 |

## Evidence findings

All nine manifest-pinned original source files match their recorded SHA256. The source index uses exact raw-file hashes plus PDF page/character or HTML visible-text/character locators. PDF page 67 (printed page 68) was visually inspected and confirms the full context for the one-year and three-year inspection-period proposals, including conditions and exceptions.

The five generated candidates are proposals only. They are not entered into remediation because no trusted reviewer supplied an explicit ACCEPT adjudication. Even after a future ACCEPT, V16.3 refuses to bypass the current V16.2 whole-literal contract: a prose-to-scalar binding incompatible with that contract stops with `V162_CONTRACT_INCOMPATIBLE` rather than rewriting source text. The nine condition issues no longer borrow an object-value locator; without `condition_ast.raw_text` that explicitly establishes the connective, they remain NEEDS_MORE_EVIDENCE.

Reviewer input requires a separately supplied trusted-reviewer registry and an adjudication bound to the immutable binding hash. Source/hash/quote/locator, entity/version/issue identity, predicate, applicability, type, reviewer identity and decision are all revalidated. ACCEPT is the only decision that may enter the evidence adapter. Enum values remain rejected until a hashed authoritative controlled-vocabulary contract is supplied.

All 79 review work items preserve their stable V16.2 issue IDs. Current Decision and Reviewer Note data are read-only audit inputs; they never enter a mutation payload. All 70 entity/version/page mappings remain unchanged in this no-accept run.

## Verification

```text
182 passed
V163_SOURCE_BINDING_ACCOUNTING_GATE_PASS issues=79 candidates=5 accepted=0
V163_READINESS_GATE_PASS canary_records=0 authorized_to_execute=false
REMEDIATION_LEDGER_GATE_PASS total=79 resolved=0 hold=11 needs_review=68
PHASE_F_READINESS_GATE_PASS canary_records=0 authorized_to_execute=false
FINAL/REPLAY BYTE AND HASH EQUALITY PASS
```

The supplied V16.3 readiness gate and unchanged V16.2 gates passed. The repository-aware V16.3 gate independently reloads the authoritative V16.2 ledger, re-extracts all manifest-pinned source bytes, verifies every span and proposal, checks the saved input/code manifest, and confirms the empty accepted-binding/evidence outputs. The authoritative `final-002` and independent `replay-002` artifacts are byte-identical.

## Artifact SHA256

Authoritative directory: `v163/artifacts/final-002`.

| Artifact | SHA256 |
| --- | --- |
| v163_review_pack.jsonl | `9d634d296473a5a96f0c7838f5e36f13ea8db9ae1609395697591f1e5988ea2c` |
| v163_source_span_index.json | `f98334d56ac94a440682c52e86fa49b7c33c4ae89453279d8155e3f07d6f9c25` |
| v163_binding_candidates.jsonl | `6be61609a8943e9341c8c5824885f276394bad9276fac984d5c3c0187049bf85` |
| v163_adjudications.jsonl | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| v163_accepted_bindings.jsonl | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| v163_rejected_bindings.jsonl | `0b3b521d7d8651f1dff1eeaeba87461c4c26454b0c2f212ec796c9cb3243374d` |
| v163_unresolved_queue.jsonl | `954aab713440aa3478e55e44274ee662ace19b7caf0734747a7a73bceae728fa` |
| v163_resolution_reconciliation.json | `79219bf048d238b40603c1f42c84f27f456901d41955979138f3650cec5dcd69` |
| v163_readiness_report.json | `6aebf71ad3970cd72a6f0add0b9c0db9191e0141c07bcb9ba6e2dfe947b35af1` |
| v163_phase_f_canary_plan.json | `47498c872cfc7611cd1af469196676c73b5726b148bf3eca1b143690964773ee` |
| v163_v162_evidence_input.json | `ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356` |
| v163_input_manifest.json | `5637b06714b1a1bc04aa2c201f9502206bfdc274d432cf773958c21a843c947b` |
| artifact_hashes.json | `aeeb090028b9b1d6c8b024468b134114cfb0bac6bc5afab1db01fe1ce98c10cd` |

V16.3 is not canary-ready yet. A reviewer must adjudicate candidates and any accepted binding must pass the unchanged V16.2 contract and full readiness gates. No Phase F canary was executed or authorized.
