# Prompt: implement V16.2 data-quality remediation and Phase F readiness — NO_WRITE

You are continuing the existing Knowledge Factory repository from a verified V16.1 checkpoint.

## Verified checkpoint that must remain true

- V16.1 canonical production plan SHA256 is exactly:
  `af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399`
- Kaggle remote verification v2 passed in NO_WRITE mode.
- Notion remote staging passed with 3 synthetic UPDATEs, independent read-back, zero-delta replay, and verified rollback.
- Latest full suite immediately before staging execution: 103/103 PASS.
- Production writes: 0.
- Human-field writes: 0.
- SQL, scheduler, production schema changes, production publication: none.
- Known data-quality findings: 79 issue entries = 70 unstructured object values + 9 ambiguous condition/connective entries.
- Existing HOLD/REJECTED decisions always take precedence over old baseline state.
- Phase F is NOT authorized by this prompt.

## Objective

Build V16.2 as a deterministic, auditable remediation layer that:

1. inventories and accounts for every known issue entry;
2. converts only evidence-backed unstructured object values into the typed V16.1 contract;
3. never guesses ambiguous AND/OR/NOT semantics;
4. preserves human decisions/notes and current HOLD/REJECTED precedence;
5. produces a new NO_WRITE canonical plan and eligible production subset;
6. produces, but does NOT execute, a Phase F canary plan;
7. proves identity/mapping stability and deterministic replay;
8. leaves the verified V16.1 implementation and remote staging history intact.

## Absolute prohibitions

Do NOT:

- PATCH/POST/DELETE any production Notion page or schema;
- run a production SQL statement or migration;
- enable a scheduler or mutation loop;
- run another Kaggle kernel/upload unless separately authorized;
- auto-resolve a connective whose meaning is ambiguous from evidence;
- infer a quantity/unit/enum/boolean from text merely because it looks plausible;
- change Decision, Reviewer Note, Reviewed Entity ID, or Reviewed Version ID;
- reinterpret HOLD/REJECTED as APPROVED;
- claim Phase F approval or production publication readiness merely because tests pass.

## Stage A — freeze and reproduce the checkpoint

1. Inspect the current working tree. Do not import the older nested reference ZIP over verified code.
2. Run the current full suite; record exact test count/result.
3. Reproduce the V16.1 real-baseline NO_WRITE plan and require the exact hash above.
4. Verify the V16.1 source/notebook/package manifest currently in the repo still matches the approved assets, where that manifest exists.
5. Read the latest live Notion review properties in read-only mode if the connector is already available. Do not request a broader permission scope.
6. Reproduce the 79-entry issue inventory from current artifacts/live read snapshot rather than hard-coding 79 rows into application logic.

Gate A: if baseline hash changes or issue inventory cannot be reconciled, STOP with `V162_BASELINE_RECONCILIATION_FAIL`.

## Stage B — introduce a namespaced V16.2 remediation layer

Prefer a new namespace such as `src/kf_pilot/v162_remediation/` rather than mutating stable V16.1 semantics in place.

Implement these concepts:

### 1. RemediationIssue

Required fields:

- `issue_id` — stable deterministic ID
- `entity_id`
- `version_id`
- `page_id` when mapped
- `issue_type` — exactly one of:
  - `OBJECT_VALUE_UNSTRUCTURED`
  - `CONDITION_CONNECTIVE_AMBIGUOUS`
- `source_text`
- `source_evidence_refs` — non-empty list for any resolved item
- `before_value_hash`
- `resolution_status` — one of `RESOLVED`, `HOLD`, `NEEDS_REVIEW`
- `resolution_rule` — required only for RESOLVED
- `structured_value` — required only for resolved object-value issues
- `condition_ast` — required only for resolved connective issues
- `after_value_hash` — required only for RESOLVED
- `review_reason` — required for HOLD/NEEDS_REVIEW
- `decision_snapshot`
- `reviewer_note_snapshot`

### 2. Typed object values

Use only the typed contract already supported by V16.1. Do not invent a new semantic type unless the current repository contract already permits it.

A conversion may be `RESOLVED` only if a deterministic rule can be proven from source evidence, for example:

- exact numeric value + explicit unit -> quantity;
- exact member of a controlled vocabulary -> enum;
- explicit true/false statement with no qualifier -> boolean;
- exact structured literal already present in an authoritative source -> matching typed object.

If unit, scope, polarity, cardinality, or enum mapping is uncertain, status is HOLD or NEEDS_REVIEW.

### 3. Condition AST remediation

For the 9 ambiguous connective issues:

- preserve original text;
- resolve AND/OR/NOT only when syntax/evidence determines one interpretation;
- otherwise keep `HOLD`/`NEEDS_REVIEW`;
- never use an LLM score alone to choose the connective;
- require a normalized AST hash for every resolved condition.

## Stage C — issue ledger and invariants

Generate deterministic artifacts under a new output directory, never overwrite prior evidence:

- `v162_issue_ledger.json`
- `v162_resolution_report.json`
- `v162_unresolved_review_queue.json`
- `v162_canonical_plan.json`
- `v162_eligible_subset.json`
- `v162_phase_f_canary_plan.json`
- `v162_readiness_report.json`
- `artifact_hashes.json`

The issue ledger must account for every discovered blocker exactly once. Duplicate issue IDs or duplicate entity/version/issue-type keys are fatal.

Required invariants:

- no issue disappears silently;
- RESOLVED requires evidence + deterministic rule + changed/validated hash;
- HOLD/NEEDS_REVIEW remains excluded from eligible publication subset;
- live HOLD/REJECTED remains excluded regardless of technical remediation;
- human-owned fields are copied into audit bindings only, never into mutation payloads;
- stable entity IDs, version IDs and page mappings are preserved unless the V16 identity algorithm intentionally produces a new version due to an actual semantic structured-value change;
- reverse-order replay is deterministic;
- a one-row remediation change changes only the expected version-level output, not unrelated entities/mappings.

## Stage D — build the NO_WRITE eligible subset

Re-run canonical planning against the remediated representation.

For every proposed production UPDATE classify it as:

- `ELIGIBLE_CANARY`
- `BLOCKED_DATA_QUALITY`
- `BLOCKED_HUMAN_DECISION`
- `UNCHANGED`

An entity may be `ELIGIBLE_CANARY` only if:

- it has no unresolved blocker;
- live decision is not HOLD/REJECTED;
- mapping is unique and present;
- schema types match current production schema or the payload uses only already-supported fields;
- planned payload contains no human-owned field;
- operation is UPDATE, never CREATE;
- target parent/page matches the known production mapping;
- before-image can be obtained read-only;
- semantic delta is non-zero and deterministic.

Do not require all 70 records to become eligible. A clean subset is acceptable. Never lower quality gates merely to create a canary candidate.

## Stage E — create but DO NOT execute Phase F canary plan

Produce a canary plan containing at most 3 `ELIGIBLE_CANARY` records. Prefer records with:

- deterministic quantity/enum/boolean remediation;
- no ambiguous condition;
- no HOLD/REJECTED status;
- minimal field delta;
- complete page mapping and before-image availability.

The canary plan must include:

- production page ID;
- entity/version IDs;
- exact intended system-owned field delta;
- before-image hash;
- expected after-image hash;
- rollback payload/hash;
- exclusion proof for human fields;
- target-parent proof;
- reason this record was selected;
- explicit `authorized_to_execute: false`.

If zero records qualify, emit an empty canary plan and PASS V16.2 remediation if all accounting/gates pass. Do not manufacture eligibility.

## Stage F — tests

Add tests covering at minimum:

1. all issue entries accounted exactly once;
2. duplicate issue ID blocked;
3. resolved item without evidence blocked;
4. resolved item without deterministic rule blocked;
5. ambiguous connective cannot auto-resolve;
6. explicit AND/OR/NOT evidence resolves deterministically;
7. ambiguous unit blocked;
8. exact quantity conversion allowed;
9. exact enum conversion allowed;
10. explicit boolean conversion allowed;
11. HOLD/REJECTED precedence preserved;
12. reviewer note/decision preserved in bindings;
13. human-owned field in plan blocked;
14. CREATE blocked;
15. missing mapping blocked from eligible subset;
16. mapping collision blocked;
17. schema mismatch blocked;
18. reverse-order replay deterministic;
19. one-row remediation locality test;
20. canary plan max size 3;
21. canary plan `authorized_to_execute` must be false;
22. no network/write path required for local test suite.

Run the full repository suite, not only new tests.

## Stage G — final execution record

Return an exact report with:

- full test count/pass;
- V16.1 baseline hash before/after;
- discovered issue count by type;
- resolution count by `RESOLVED/HOLD/NEEDS_REVIEW`;
- unresolved issue count;
- number of eligible canary records;
- number blocked by data quality;
- number blocked by human decision;
- CREATE count;
- mapping collision/missing count;
- human-field write count;
- production write count;
- SQL count;
- scheduler action count;
- schema mutation count;
- hashes of every V16.2 artifact;
- exact final status.

Allowed final statuses:

- `V162_REMEDIATION_PASS / PHASE_F_NOT_AUTHORIZED`
- `V162_REMEDIATION_BLOCKED`
- `V162_BASELINE_RECONCILIATION_FAIL`

A PASS means the remediation/readiness computation is trustworthy. It does NOT authorize execution of the Phase F canary.
