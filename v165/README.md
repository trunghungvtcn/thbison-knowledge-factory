# V16.5 local complete-record implementation

Scope: LOCAL / NO_WRITE. The new namespace is `kf_pilot.v165_complete_record`.
Existing V16.1–V16.4 code and artifacts remain input-only. The extension uses the
existing `claim_version_id` algorithm and a distinct `complete_record_derivation/v1`
route. `legacy_literal/v1` calls the unchanged V16.2 resolver without fallback.

## Commands from the repository root

Use the existing Python environment with `src` and test dependencies on PYTHONPATH.

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH=((Resolve-Path 'src').Path+';'+(Resolve-Path '.v161-test-deps').Path+';'+(Resolve-Path '.deploy-test-deps').Path+';'+(Resolve-Path '.test-deps2').Path)
$py='C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m pytest -q
& $py -m kf_pilot.v165_complete_record run --output v165/artifacts/final-001
& $py -m kf_pilot.v165_complete_record run --output v165/artifacts/replay-001
& $py -m kf_pilot.v165_complete_record verify v165/artifacts/final-001 v165/artifacts/replay-001
```

Choose new output directories for subsequent runs. Existing artifacts are never
overwritten. The CLI exposes only proposal generation and verification; there is
no remote write or real-data apply flag.

## Contract and review boundary

The exact supplied `contracts/COMPLETE_RECORD_V1.md` bytes are the contract spec.
Their SHA256 is recorded in every draft and activation-status artifact. The
activation template remains NOT_APPROVED. No trusted issuer, semantic reviewer,
activation receipt or ACCEPT was invented.

The same `core.project` implementation runs synthetic positive tests and validates
repository-class bundles. Its arguments require an explicit expected parent,
schema, independent receipt roots and their pins, current records/issue state,
and a raw-source store. It stages changes in copies and returns them only after
all checks; exceptions leave original data unchanged. Receipt pins must come from
an independently approved authority channel, never from candidate content.

For the real pilot, `target_version_id` remains null while evidence completeness
is UNKNOWN. The quantity change is a reviewable draft; inherited condition and
exception ASTs remain visible in before/after views with explicit blockers.

Missing future inputs (not permissions for this run):

- `v165/inputs/reviewer_registry.json`: independently supplied issuer/reviewer
  registry, role, predicate/entity scope, validity interval and data class.
- `v165/inputs/contract_activation.json`: APPROVE_LOCAL_SHADOW receipt binding
  the exact published spec hash, predicate/entity allowlists and registry hash.
- `v165/inputs/complete_record_adjudications.jsonl`: whole-record adjudication
  only after a complete proposal and final target version exist.
- Pinned evidence/review for condition grouping, clauses 10.2–10.4, cross-rule
  precedence and the inherited legal-validity assertion. Current legal validity
  is not asserted from the 2016 source or from a Notion property.

The full real ledger has all original issue IDs plus separately identified new
blockers. `apply_status=NOT_EXECUTED` means no real semantic resolution occurred.
Production eligibility is NOT_EVALUATED, not certified zero-ready. The output
canary is deliberately empty and `authorized_to_execute=false`.

## Evidence and snapshots

Source pages are re-extracted with the pinned PyMuPDF version and checked against
V16.3's source catalog. All text units in the pinned QTKD source are included as
context; exact quantity spans retain raw offsets. Source page ordinal 67 maps to
index 66 and the printed page 68. Poppler-rendered pages were visually inspected.
Cross-reference current validity is still missing and marked as such.

Only the two pilot Notion pages and schema were fetched again read-only. Their
responses and retrieval timestamp are local in `inputs/pilot_reviews.json`.
The other 68 human snapshots remain the pinned V16.3 snapshots; no claim is made
that all 70 were refreshed. No SQL connector query was executed.

## Package privacy

The code ZIP contains allowlisted implementation/tests/docs and non-sensitive
verification logs. The private audit ZIP contains real draft/evidence artifacts
and page/reviewer snapshots; retain it locally unless separately authorized to
share. Neither archive includes credentials, tokens, dependencies or caches.
