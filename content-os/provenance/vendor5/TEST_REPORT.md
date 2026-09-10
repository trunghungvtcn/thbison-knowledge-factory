# Vendor 5 TEST_REPORT Fix R2

Ran: 2026-09-10T07:36:10Z
Python: 3.10.21 (supported: 3.10, 3.11, 3.12 x86_64)
verify_local: VERIFY_LOCAL_OK (fail-closed)
JUnit (verify_local): 43 passed, 0 failed (CMS-01..26 + R2 policy; excludes recursive fail-closed script tests)
pytest tests/test_verify_fail_closed.py: 3 passed (pip_check/worker/restart_assert inject → nonzero, no success receipt)

| Gate | Status |
|---|---|
| clean install | PASS offline wheelhouse (cp310/311/312 rpds) |
| schema pin | PASS |
| regression | PASS 43 in verify_local |
| HTTP | PASS |
| OS process restart | PASS |
| verify_local fail-closed | PASS 3 inject cases |
| actual CMS | NOT_RUN MOCK |
| staging CMS | BLOCKED_MISSING_INPUT |

REPRO.py old: unexpected_acceptance true. New: AdapterError POLICY_MISMATCH (not an import crash). Suite asserts code.
