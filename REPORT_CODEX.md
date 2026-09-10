# THBISON-INTEGRATION-01 candidate report

Verdict: **HANDOFF_WITH_BLOCKERS**

Data class: **TEST_ONLY**
`live_data_pass=false`; `notion_status=NOTION_TARGET_MISSING`; no VPS deploy and no public/production effect occurred.

## Gate results

| Gate | Result | Evidence / limitation |
|---|---|---|
| G0 | PASS | Outer package and Content OS SHA-256 verified; exact five source pins recorded; core→J1→J2→bridge deltas applied without conflict; vendor namespaces and NOTICE retained. |
| G1 | BLOCKED | V1/V2 clean install, typecheck, tests and Node 22 builds pass. PGLite build fallback works, but an isolated external PostgreSQL migration was not available on this Windows runner. |
| G2 | BLOCKED | Strict Knowledge source/hash behavior is integrated, but the complete J1 suite requires the Linux CI runner because the pinned contractor locator is POSIX-only. |
| G3 | BLOCKED | Local contractor result was 82/101 (M1 13/18, M2 17/17, M3 18/18, M4 27/27, M5 7/21); the remaining failures are Windows/POSIX transport cases. Linux CI is the required independent collection run. |
| G4 | BLOCKED | Local bridge jobs were 20 pass/20 fail on the same POSIX-locator boundary. V6 was 70 pass, 1 fail, 2 skip: the pinned staging fixture's stored contract digest does not match its recomputed digest. |
| G5 | PASS | Actual-process TEST_ONLY chain executed V1→Knowledge/V4→V2→V3→V5 under V6; identity/digest/approval bindings matched and CMS stayed DRY_RUN. |
| G6 | PASS | V3 persisted state survived restart, V3 alone owned retry, repeated requests were idempotent, CMS receipt reported zero actual effects. |
| G7 | BLOCKED | V1/V2 auth tests and production builds pass, but browser desktop/mobile screenshots were not produced on this runner. |
| G8 | PASS | Explicit deterministic Knowledge-output→EvidenceBundle mapping and schema validation pass; missing/unverified/hold input remains blocked. Real Knowledge input is not present. |
| G9 | NOT_RUN | No explicit project-owned Notion sandbox target was provided; status is `NOTION_TARGET_MISSING` and no Notion write was attempted. |
| G10 | PENDING_RELEASE | Sanitized deterministic assets and download re-hash are completed during release publication. |

## Reproduction

```text
python scripts/labctl.py up
python scripts/verify_candidate.py
python content-os/modules/vendor6/scripts/run_actual_integration.py
python scripts/labctl.py down
```

Full Linux verification is `python scripts/verify_candidate.py --full`; the pinned GitHub Actions workflow additionally performs V1/V2 clean builds, V5/V6 suites, actual-process E2E, and sanitized evidence upload.

## Actual-process result

`ACTUAL_PROCESS_SYNTHETIC_PASS`: public effects 0; V3 final/read-after-restart `SUCCEEDED`; retry owner `vendor3`; CMS `DRY_RUN`; Notion `NOTION_TARGET_MISSING`.

This report does not claim production readiness. Grok must independently verify G0–G10 from the release SHA and assets and report through the single audit issue.
