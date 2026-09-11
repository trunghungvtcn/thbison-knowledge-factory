# CMS discovery (Vendor 5)

Sources used: contracts/BEHAVIOR.md, PublishRequest/PublicationReceipt/ArticlePackage/ApprovalRecord schemas, Vendor2 `src/lib/content-os/cms.ts` (unaccepted candidate), ACCESS_POLICY.md, STAGING_ACCESS_MANIFEST.json.

## Product / version / plugin
- Native CMS product: UNKNOWN. Package contains no CMS staging base URL, plugin list, or verified GitHub revision.
- thbison.vn WooCommerce existence does not prove a current article/REST endpoint. Not used.
- Simulator product: THBISON-CMS-SIM version sim-1.0.0 (lab only).

## Authentication
- Adapter service auth: `Authorization: Bearer test-service` in MOCK. MOCK identity is rejected if ALLOW_PRODUCTION=true.
- Native CMS auth: UNKNOWN / BLOCKED_MISSING_INPUT (CMS_STAGING_TOKEN empty by policy).

## Routes
- Public THBISON adapter routes (OpenAPI 1.0.0): `/healthz`, `/v1/capabilities`, plus Vendor 5 proposed `/v1/publications` and reconcile/rollback (PROPOSED extension, not a change to frozen schemas).
- Native CMS draft/update/media routes: UNKNOWN. Not guessed.

## Draft / update / media lookup
- Vendor2 mock `cmsCreateDraft` keys drafts by project|destination|article|revision|content hash and supports timeout-after-accept without a second create.
- Native lookup/idempotency: UNKNOWN. Adapter therefore fail-closes: persist UNKNOWN and reconcile via external key lookup on the simulator; never blind-retry create when lookup is disabled.

## Idempotency
- Adapter ledger key: project + destination + operation + Idempotency-Key + canonical payload hash.
- Simulator key: project + destination + external_key (article_id:revision:content_sha256).
- Provider Idempotency-Key semantics: UNKNOWN for any real CMS.

## Revisions
- Simulator supports integer revisions and optimistic update. Human edit increments revision; stale expectedRevision is rejected and body preserved.

## Sanitization / limits
- Script tags, javascript: URLs, onerror/onload handlers blocked.
- Destination host allowlist; link-local/metadata IPs blocked.
- Citations of the form `[claim:…]` must survive sanitization.
- LIVE and public publish disabled. Envelope 2 MiB per contract.

## Capability limits
- DRY_RUN: validate, zero mutations.
- STAGING_DRAFT: only when STAGING_WRITE_ENABLED and data_class=STAGING and destination allowlisted.
- LIVE: denied at vendor acceptance regardless of contract enum presence.
