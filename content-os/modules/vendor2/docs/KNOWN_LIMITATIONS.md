# Known limitations — Vendor 2 Content OS

Honest labels. Do not merge these into a single “pass”.

## Not run / blocked (by design of this contractor drop)

| Item | Label | Why |
|------|-------|-----|
| S01–S18 | `NOT_RUN` | Owned by Vendor 1. Out of this module. |
| A1–A8 assembly | `BLOCKED_EXTERNAL` | No access to THBISON Knowledge, CMS, OpenSEO, Facebook, or VPS B. |
| Real CMS adapter | `NOT_RUN_EXTERNAL` | Mock CMS only. Timeout-after-accept is unit-tested against the mock. |
| Knowledge retrieval | SYNTHETIC | Fixture evidence bundles, not live retrieval. |
| OpenSEO | SYNTHETIC | Planning keywords marked `measurement_status=SYNTHETIC`. |
| Facebook posting | flag off | Summary card only; `posting=false`. |
| P01–P05 on VPS B | `NOT_MET` | No compatible Vendor 1 baseline on the assembly VM. |
| P05 15% vs baseline | `NOT_MET` | Preview-host timings are **not** evidence for this goal. Do not cite them as a 15% win. |
| Process restart durability | file-snapshot simulator | PGLite preview is in-memory. Tests round-trip a file snapshot. Production durability is the team's `DATABASE_URL`. |
| Kit self-test | `PARTIAL` | 50 passed, 1 failed (`test_naive_date_rejected`). Kit tests were not modified. This is **not** acceptance complete. |
| `ADAPTER_VERIFIED` | never claimed | No real provider credentials were used. |
| `INTEGRATED_CANARY_PASS` | never claimed | No canary deploy. |

## Bound residuals (documented, not silently dropped)

- HTTP maps internal gate codes such as `TEST_DATA_NOT_PUBLISHABLE` to schema `Error.code` `VALIDATION_ERROR` (OpenAPI enum). The gate still throws the specific code in-process.
- HTTP POST job endpoints admit `QUEUED` and return 202 without waiting. Processing is a `QueuePort` (`src/lib/content-os/queue.ts`) that Vendor 3 replaces; `processContentJob` / `processPlanningJob` stay Vendor 2 business logic.
- Social composer is display-only.
- Pilot risk SAFETY/LEGAL is blocked for publication even if a fixture tried to mark it ELIGIBLE.

## Security notes

## Release packaging

- `artifact_digest` is SHA-256 of `payload.tar.gz` (git archive of `source_commit`), not a self-hash of the envelope ZIP.
- Envelope ZIP hash is the sidecar `*.zip.sha256`. Putting that digest *inside* the ZIP would make the hash circular.
- Docker image: `NOT_BUILT` (no daemon in the contractor sandbox). Dockerfile + compose are shipped.

- Logs redact bearer tokens, `sk-` keys, and `X-Amz-Signature` query strings.
- Artifacts refuse `..` path segments.
- Live/staging/social flags default false and are not UI-toggleable.
