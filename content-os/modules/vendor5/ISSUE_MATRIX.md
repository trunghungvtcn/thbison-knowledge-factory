# ISSUE_MATRIX Vendor 5 R2

| ID | Status | Evidence |
|---|---|---|
| R2 HIGH policy_version bind | FIXED | test_r2_policy.py, evidence/repro_new.txt |
| R2 MEDIUM verify_local fail-closed | FIXED | test_verify_fail_closed.py |
| R2 clean install 3.12 ABI | FIXED (wheels added; not executed here — host is 3.10) | vendor/wheelhouse rpds cp312 |
| Native CMS | BLOCKED_MISSING_INPUT | |
| Vendor3 actual retry | NOT_RUN (local port) | |
