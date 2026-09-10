# FIX_RESPONSE Vendor 5 R2

## HIGH policy binding
Root cause: app/adapter.py::_authorize compared hashes/ids/destination but not policy_version.
Fix: require article.policy_version == approval.policy_version == evidence.policy_version; also data_class and bundle_id.
Before: REPRO.py unexpected_acceptance DRY_RUN. After: POLICY_MISMATCH, sim.side_effects==0.
Tests: tests/test_r2_policy.py (mismatch dry-run/staging/article/evidence + positive control).

## MEDIUM verify_local
Root cause: set +e around worker/assert/pip check; always wrote VERIFY_LOCAL_OK and restart exit_code:0.
Fix: run_gate captures rc and fail(); rm success receipt; restart assertion uses durable side_effects==1.
Regression: VERIFY_INJECT_FAIL=pip_check|worker|restart_assert → nonzero, no receipt.

## Clean install
Added cp311/cp312 rpds wheels. Script rejects unsupported Python early.

acceptance_claimed=false
