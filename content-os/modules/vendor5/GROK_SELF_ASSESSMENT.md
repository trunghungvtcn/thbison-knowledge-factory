# Vendor 5 self-assessment Fix R2
acceptance_claimed: false
Module: VENDOR_5
Contract: fd3c1b6f1ec5461e7080c538e1c332d7af3098db32edd1565e1ae16933f951a8

| Issue | Root cause | Change | Before/after | Regression | Evidence | Remaining |
|---|---|---|---|---|---|---|
| HIGH policy bind | _authorize skipped policy_version | Compare article/approval/evidence policy_version | DRY_RUN accepted different-policy → POLICY_MISMATCH zero effects | test_r2_policy_* + REPRO.py | evidence/repro_new.txt junit | Canonical hash profile still needs owner golden vectors for integration |
| MEDIUM verify_local | set +e; ignored pip check/worker/assert | run_gate fail-closed; no receipt on fail | VERIFY_LOCAL_OK despite assert fail → exit nonzero | test_verify_fail_closed.py | junit | inject env is test-only |
| clean install ABI | only cp310 rpds | add cp311+cp312 wheels; fail early on other Python | 3.12 EXIT 2 → pip --no-index should succeed on 3.12 x86_64 | docs/RUNTIME.md | wheelhouse | Not every OS/arch |
| RuntimeRetryPort | local class owner=vendor3 | unchanged, documented MOCK | n/a | KNOWN_LIMITATIONS | | not actual Vendor3 |
| Native CMS | simulator | still MOCK | n/a | | BLOCKED_MISSING_INPUT |

Không tự nghiệm thu.
