# V16.2 remediation — offline only

The unpacked user package is retained under `vendor/v162-deployment-pack`. Its prompt was read in full; its older nested V16.1 ZIP was NOT installed. Production V16.1 sources remain unchanged.

Implementation: `src/kf_pilot/v162_remediation`. The module imports only local semantic helpers and standard-library computation; it has no HTTP transport, token handling, SQL, scheduling, or canary execution.

From the project directory:

```powershell
python -m pytest -q
python v162/run_remediation.py --output v162/artifacts/new-run
python vendor/v162-deployment-pack/v162/gate_remediation_ledger.py v162/artifacts/new-run/v162_issue_ledger.json
python vendor/v162-deployment-pack/v162/gate_phase_f_readiness.py v162/artifacts/new-run/v162_readiness_report.json v162/artifacts/new-run/v162_phase_f_canary_plan.json
```

Always choose a new output directory. Saved raw Notion reads cover all 70 production pages and the schema. They are audit snapshots, NOT a continuing live feed. Refresh read-only review snapshots before future readiness computations; stale eligibility must never be executed.

## Evidence policy

This baseline contains prose, headings, compound obligations, numeric percentages unsupported by the V16.1 quantity contract, and legacy condition tags. A source relation/URL is not sufficient proof of a typed conversion. No reviewed, scope-bound structured evidence bindings were supplied for this run. All 79 issues remain explicitly accounted for and unresolved. This is a trustworthy accounting PASS, not a claim that product data is repaired or publication-ready.

An optional `--evidence path.json` accepts reviewed bindings keyed by ledger issue ID. Each must identify entity/version/field, source ref, complete content and its raw UTF-8 SHA256, an exact whole literal, and explicitly reviewed authoritative/scope flags. These assertions must come from verified source review, not model guesses. Quantity/boolean/enum conversions only accept the entire source object literal. Controlled enums additionally require a vocabulary ref and canonical vocabulary SHA256. Condition conversion accepts an explicit validated AST literal with verified scope, never a guessed operator over tags. Arbitrary prose and qualifiers remain in review. Invalid evidence cannot disappear blockers. The CLI records the evidence-file hash; retain the supplied source evidence alongside it for audit.

Eligibility additionally requires unique mapping, current review not HOLD/REJECTED, no source HOLD, correct parent/legacy identity, supported existing property types and a nonzero system delta. Existing nonempty rich-text before-images are ineligible until full typed metadata is available (connector text alone loses formatting). No implicit schema expansion. Canary size is at most three and authorization is always false.

The bundled independent gates are run unchanged. Stronger internal gates recompute ledger evidence/hashes and reject missing readiness counters, unknown/human fields and canary tampering. Neither gate nor a PASS authorizes Phase F.
