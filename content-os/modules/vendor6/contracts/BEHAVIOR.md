# Shared behavior contract 1.0.0

## Authority and compatibility

JSON Schema defines shape; this file defines required BEHAVIOR. Neither alone proves semantics or external integration.
`contracts/openapi.json` specifies NEW THBISON adapter routes, not native OpenSEO, Notion or CMS endpoints.
Owner pins `CONTRACT_SHA256.txt`. Both providers and consumers are tested against that exact revision.
Unknown contract version/digest fails with UNSUPPORTED_CONTRACT. No silent fallback.
All object schemas are strict. Do not add ad-hoc fields; use a versioned change approved by the owner.

UTF-8 transport; schema field names ASCII; Vietnamese text preserved. Do not globally strip diacritics.
Hash profile for ArticlePackage/EvidenceBundle: sorted ASCII schema keys, compact JSON, ensure_ascii=true,
no floats in these hashed objects, lowercase hex SHA256; omit ONLY the object's own hash field.
Cross-language implementations must match examples and Unicode test vectors, not assume default JSON serialization.
Content/evidence snapshots are immutable. IDs stay stable across releases; revisions change when semantics change.

## Common HTTP and job rules

- Authenticated TLS outside loopback development. Bind verified server identity to project; caller project_id is not proof.
- Service credential is least privilege and not exposed in browser code. Human editorial approval uses an authenticated
  human session and role check; do not let agents self-grant can_publish or create ApprovalRecord arbitrarily.
- Every request has X-Contract-Version; every POST has Idempotency-Key. Scope keys to project+operation.
- Identical key+payload returns the original logical object (even after restart), different payload -> 409.
- Persist admission transaction before side effects. At-least-once transport, idempotent business effects;
  do not advertise exactly-once network execution.
- POST job returns 202 promptly; work proceeds with a finite budget/deadline. GET reports terminal state or bounded progress.
- Preserve first request identity when an equivalent retry uses a new trace ID; trace IDs are not logical idempotency keys.
- Cancellation records a terminal decision and prevents new provider calls. An in-flight CMS result still needs reconciliation.
- 429/5xx may be retried within the GLOBAL job budget; honor Retry-After. 401/403, validation and hash failures
  are not endlessly retried. Attempts across restarts and nested SDKs count toward the same budget.
- max_provider_requests and token/cost ceilings are reserved transactionally before calls; account for unknown charged
  outcomes. Do not release a reservation on timeout unless non-charge is confirmed.
- Query/cache key includes project, locale, provider revision, normalized seeds, freshness window and policy.
- Never derive an outbound URL, SQL path, file path or shell command directly from model text.
- `/healthz` only liveness; `/v1/capabilities` must report version, contract digest, code commit, fixture/live mode and
  supported destination operations without leaking credentials. These two operational routes and their schemas are included in OpenAPI. Liveness is unauthenticated; capabilities requires service authorization.

## SEO and briefs

ResearchResult keeps measured / missing / stale / synthetic separate. Missing values are null, not 0.
Metrics retain provider source reference, country, language and measurement timestamp.
SEO opportunity ranking is NOT truth/safety scoring. Competitor content is not primary technical evidence.
ContentBrief is a content request, not factual proof. It includes audience, intent, questions, outline, product references,
evidence requirements and constraints. Manual briefs explicitly use origin=MANUAL and never fake research metrics.
Research and ContentBrief are frozen revisions. Planning edits create a new revision and invalidate dependent draft approval.
Keyword reuse and content cannibalization are explicit recommendations, not silent deletion or rewriting of existing pages.
Vendor 1 also provides a documented output fetch for completed job artifacts; authenticated IDs, not public signed URLs in logs.

## Evidence and articles

Knowledge status ELIGIBLE means suitable for specified uses under the supplied policy, NOT APPROVED by a human.
The internal exporter maps legacy statuses without overwriting them. HOLD/QUARANTINE -> no permitted use.
Before generation and immediately before publishing, obtain current revocation/policy state through the trusted gateway.
A stale snapshot can be retained for audit but cannot overrule a revoked source.
ArticlePackage links every factual block to known claim IDs and source versions. Quote hash and source locators must check.
Fact-to-source reference validation alone does not prove semantic entailment: vendor must evaluate paraphrases, units,
negations, model scope and jurisdictions on curated cases and report uncertain statements visibly.
Do not disguise facts as EDITORIAL/CTA to avoid citation checking. No source -> omit the factual assertion and flag the gap.
Unresolved blockers -> REVIEW_REQUIRED, never a green 'ready to publish' badge.
No safety or legal instructions are published in this pilot. Supporting UI may display excluded content as clearly marked gaps.
Do not substitute OEM facts for THBISON product facts without matching evidence. No automatic image generation is required.

## Approval and publishing

ApprovalRecord is issued/stored by the trusted editorial service. A public caller cannot supply an authoritative approval.
Bind it to project, exact article revision, full content hash (including SEO fields), evidence snapshot, policy and destination.
Editing ANY bound field, changing evidence or revoking approval blocks publishing until re-approved.
Publisher retrieves and validates the server-side record; a request approval_id or status='APPROVED' alone is insufficient.
Use DRY_RUN by default. TEST_ONLY data NEVER has external effects. STAGING_DRAFT writes only to an allowlisted nonpublic
sandbox and does not expose public pages. LIVE requires current PRODUCTION data, permission AND deployment enable flag.
Planning dates do not authorize publication. Store aware UTC instants and display Asia/Bangkok. VPS B owns the single timer;
Content OS owns claim/approval/status transitions, publishing lease and effect ledger.
Before a write: reserve the project+article-revision+destination operation. If the provider may have accepted a request but
response is lost, status=UNKNOWN. Reconcile by a durable provider record mapping/idempotency mechanism before retrying.
Many CMS APIs do not promise Idempotency-Key semantics: DO NOT assume they do; demonstrate the adapter strategy.
UNKNOWN is never counted as success or blindly retried to create a duplicate. Return a truthful receipt.
Rollback code does not automatically unpublish articles. Unpublish/delete requires separate authorized compensating action.
Social summaries retain the approved meaning and link to the article; do not copy the entire text. Social publication
is disabled by default and requires destination-specific authorization; browser automation to bypass platform controls is excluded.

## Data storage

Notion holds long-lived records/files; runtime local storage may keep transactional job state, cache and outbox.
Vendors implement clients to the internal ArtifactGateway, not competing direct writes to Knowledge databases.
Stable artifact ID+hash+size; signed URLs are transient. Expiry -> obtain a fresh URL, not re-upload the same file.
Only mark remote storage VERIFIED after attach, re-fetch, download and checksum. Never delete pending outbox files.
Use client-side safe path handling and streaming size caps. Do not import pickle/untrusted code as a model or dataset.
No secrets/decision CSV/private historical source in fixtures. Fixtures are synthetic and stamped TEST_ONLY.

## Mock versus real modes

Mock provider port supplies fixed outputs/errors/clock. Provider protocol integration needs a separate sandbox/live probe.
No paid calls, collaborator access grants or production writes are authorized by this kit.
Missing access yields NOT_RUN_EXTERNAL with exact dependency, not fake ONLINE_PASS and not a request to make private repos public.

Completed job output is fetched from `/v1/planning/jobs/{job_id}/output` (PlanningOutput) or `/v1/content/jobs/{job_id}/output` (ArticlePackage). Non-terminal output requests return 409/JOB_NOT_TERMINAL; polling always respects the original deadline. These pilot envelopes are limited to 2 MiB JSON, with larger artifacts transferred via the internal gateway.
