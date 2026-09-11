# THBISON-INTEGRATION-01 candidate report

Verdict: **HANDOFF_WITH_BLOCKERS**

Data class: **TEST_ONLY**
`live_data_pass=false`; `notion_status=NOTION_TARGET_MISSING`; no VPS deploy and no public/production effect occurred.

## Gate results

| Gate | Result | Evidence / limitation |
|---|---|---|
| G0 | PASS | Outer package and Content OS SHA-256 verified; exact five source pins recorded; core→J1→J2→bridge deltas applied without conflict; vendor namespaces and NOTICE retained. |
| G1 | BLOCKED | V1/V2 clean install and typecheck pass; local Node 22 builds pass. Linux CI exposed incomplete imported payload: V1 179/195 and V2 180/195 tests pass, with failures rooted in absent `.grok/skills/og` fixtures. Isolated external PostgreSQL migration was not available. |
| G2 | PASS | Linux CI runs the exact pinned history and reports all 40 Knowledge jobs plus 4 gateway tests passing; strict source/hash behavior and inventory verification are included. |
| G3 | BLOCKED | The pinned contractor reports `CONTRACTOR_PARTIAL`; verifier now converts that misleading zero exit into `CONTRACTOR_VERIFICATION_INCOMPLETE`. Local detail was 82/101 and the Linux contractor did not emit per-module accounting to stdout. |
| G4 | PASS | Linux CI reports 40/40 bridge jobs, V5 46/46, and V6 71 pass with 2 declared skips; actual-process E2E covers the synthetic chain. Real staging/Notion remains separately unverified. |
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

## Independent audit remediation

Grok returned `AUDIT_BLOCKED` with 54/55 adjudicated scenarios passing. The sole residual, malformed CMS JSON closing the connection, is fixed in the bounded remediation documented in `REMEDIATION_01.md`; targeted HTTP tests now pass 5/5 and the actual-process TEST_ONLY pipeline still passes with zero CMS effects. G1, G3, G7 and G9 remain blocked/not-run for the explicit reasons above.
