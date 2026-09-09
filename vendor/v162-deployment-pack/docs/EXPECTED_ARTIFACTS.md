# Expected V16.2 artifacts

- `v162_issue_ledger.json`
- `v162_resolution_report.json`
- `v162_unresolved_review_queue.json`
- `v162_canonical_plan.json`
- `v162_eligible_subset.json`
- `v162_phase_f_canary_plan.json`
- `v162_readiness_report.json`
- `artifact_hashes.json`

Every JSON artifact should be canonicalized before hashing (UTF-8, sorted keys, stable separators, no timestamps in semantic payloads unless explicitly separated as metadata).
