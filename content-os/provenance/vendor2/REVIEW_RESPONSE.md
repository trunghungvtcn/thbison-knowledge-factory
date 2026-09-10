# Response to internal review (CHANGES_REQUIRED)

Contractor drop. MOCK / SYNTHETIC. Not acceptance-complete.

| # | Review item | Response |
|---|-------------|----------|
| 1 | Do not present near-acceptance while kit is PARTIAL | Status is `CHANGES_ADDRESSED_MOCK`. `acceptance_claimed=false`. KIT_SELF_TEST is PARTIAL (50 PASS, 1 FAIL `test_naive_date_rejected`). Kit tests unmodified. UI `/nghiem-thu` states this is not complete acceptance. |
| 2 | `artifact_digest` must be SHA-256 of the release artifact, linked to commit / tree / contract | Two-layer pack: `artifact_digest` = SHA-256 of `payload.tar.gz` (exact `git archive` of `source_commit`). Envelope ZIP sidecar is `release_zip_sha256` (cannot self-hash a ZIP that contains its own digest). All four values are in `DELIVERY_RECEIPT.json` + `RELEASE_MANIFEST.json`. |
| 3 | JUnit must not treat S01–S18, A1–A8, real-provider, P08 as PASS | Those cases are `<skipped message="STATUS: reason">`. Counts live in `docs/SCOPE_STATUS.json`. Kit junit is a **separate** file with the real 1 FAIL. |
| 4 | C03 revoke evidence needs HTTP proof | HTTP cases: `C03-revoke`, `C03-approval-invalidated`, `C03-evidence-unusable`, `C03-publish-blocked`, `C03-no-resurrect-after-restart`. |
| 5 | P05 is NOT_MET; do not cite preview p95 as 15% | P05 stays NOT_MET. P02 is MEASURED observation only, skipped in JUnit, labeled “NOT evidence for P05”. |
| 6 | Jobs processed inline before HTTP 202 | `POST` inserts `QUEUED`, `persistLedger`, `getQueue().dispatch`, returns 202. Vendor 3 replaces `setQueuePort`. `processContentJob` / `processPlanningJob` stay Vendor 2. |
| 7 | PGLite in-memory — add durable-store simulator | File snapshot under `CONTENT_OS_DURABLE_DIR` (default `/tmp/thbison-ledger`). `POST /v1/mock/ledger/restart` wipe+reload. Tests: restart, job terminal, approval history, duplicate delivery, publication receipt. Not a THBISON database. |
| 8 | Strip caches from the ZIP | Packer excludes `.grok`, `.pytest_cache`, `__pycache__`, `.vercel`, `node_modules`, `dist`, `.output`, `.vite`, preview pid/log, `attachments/`. |
| 9 | Single release ZIP with manifest, sums, hashes, honest JUnit, limitations, Docker receipt | Envelope contains `RELEASE_MANIFEST.json`, `SHA256SUMS.txt`, filled receipt, JUnit, `KNOWN_LIMITATIONS.md`, `DOCKER_BUILD_RECEIPT.json` (`NOT_BUILT`). |

No THBISON CMS / Notion / OpenSEO / Facebook / VPS B credentials were used.
