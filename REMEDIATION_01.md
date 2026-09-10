# Bounded remediation after independent audit

Input audit verdict: `AUDIT_BLOCKED` on `thbison-integration-01-rc1`.

Audit pack SHA-256: `27cf3101618e4049d367e5c148142a0d674d4c0283f7ca2dfee50bf153751b35`.

## Fixed in this round

- Residual `neg-malformed-json` at G4: V5 now converts invalid UTF-8/JSON to a deterministic HTTP 400 `VALIDATION_ERROR` envelope instead of closing the connection.
- Non-object JSON, invalid `Content-Length`, negative length, and bodies over the declared 2 MiB limit also fail closed.
- Regression coverage binds the returned request ID and verifies the exact error envelope.

## Verification

- `python -m pytest -q content-os/modules/vendor5/tests/test_http.py`: 5 passed.
- Full local V5 source suite: 45 passed; 3 Linux-only shell-injection tests NOT_RUN on Windows because `bash` is unavailable.
- Actual-process TEST_ONLY E2E: `ACTUAL_PROCESS_SYNTHETIC_PASS`, CMS `DRY_RUN`, effects 0.

## Intentionally unresolved

- V1/V2 `.grok/skills/og` and App Builder template fixtures were not present in the pinned input archive. They are not synthesized without provenance.
- Contractor remains `CONTRACTOR_PARTIAL`; its 101/101 synthetic module tests do not constitute a real Notion read.
- No project-owned Notion sandbox target, external PostgreSQL service, or complete V2 UI screenshot environment was supplied.

Candidate remains `HANDOFF_WITH_BLOCKERS`; `real_data_pass=false`, `live_data_pass=false`, and `production_ready=false`. No merge, deploy, or live write is authorized.
