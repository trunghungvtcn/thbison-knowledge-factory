# V16.2 deployment plan — remediation before production canary

## Checkpoint

V16.1 has proven the write machinery on isolated Notion staging. The remaining production risk is data correctness, not basic transport/rollback mechanics.

## Phase 1 — Reconcile

- Re-run full tests.
- Reproduce the V16.1 canonical hash.
- Rebuild the current 79-entry blocker inventory from source artifacts/live read snapshot.
- Fail if counts or identity mappings cannot be explained.

## Phase 2 — Deterministic remediation

For each `OBJECT_VALUE_UNSTRUCTURED`, attempt only evidence-backed typed conversion. For each ambiguous connective, resolve only from deterministic syntax/evidence. Anything uncertain remains HOLD/NEEDS_REVIEW.

No production write occurs in this phase.

## Phase 3 — Replay and locality

Recompute V16.2 canonical output and prove:

- stable entity/page identity;
- version changes only where semantics actually changed;
- reverse-order replay is stable;
- a single remediation edit has local, predictable effects.

## Phase 4 — Eligible subset

Partition planned production rows into eligible, data-quality blocked, human-decision blocked, or unchanged. Eligibility requires unique mapping, supported schema, no human fields, UPDATE-only, and zero unresolved blocker.

## Phase 5 — Phase F canary plan (plan only)

Select at most 3 clean records. Create before/after/rollback hashes and an explicit execution-disabled canary artifact.

This pack does not authorize the canary to run.

## GO / NO-GO

### V16.2 remediation PASS

- V16.1 baseline hash preserved.
- Every discovered blocker accounted exactly once.
- No guessed resolutions.
- Full tests pass.
- Production writes = 0.
- Canary plan is execution-disabled.

### Phase F still NO-GO unless separately approved

A later Phase F approval should explicitly name:

- exact canary page IDs;
- exact canary plan hash;
- max write count;
- rollback requirement;
- whether current production schema is accepted as-is;
- one-run-only authorization.
