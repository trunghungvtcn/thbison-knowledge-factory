# Vendor 2: Content OS workspace, drafting, review and publishing adapters

## Outcome
One usable administration UI and backend that consumes Vendor 1 briefs plus a frozen Knowledge EvidenceBundle,
generates a source-bound article, supports review/revision, and prepares a safe, idempotent staging publication.
Mock ports let development proceed before real OpenSEO/Knowledge/VPS B exists.

## In scope
- The ONLY integrated frontend shell. Includes planning/calendar UI backed by Vendor 1, brief detail/edit flow,
  job list, evidence panel, editor, desktop/mobile preview, approvals and publication history.
- Draft orchestration with pluggable LLM provider, timeout/cost caps and a fixed synthetic mode.
- Evidence retrieval client, per-block citation mapping, gaps/uncertainty view, source-scoped product claims.
- Revisioned article/SEO fields, optimistic concurrency, approval bound to immutable content+evidence+destination.
- CMS port for draft/create/readback/reconcile/schedule/cancel capabilities. Discover actual THBISON staging CMS
  through the operator; do not assume product API is a WordPress post-publishing endpoint.
- Safe unknown-result handling, destination allowlists, background execution via one VPS B timer, no second cron.
- Social summary artifact for Facebook Page with link and meaning preserved. One sandbox adapter may be delivered
  when permissions exist; actual social publication remains disabled until separately authorized.
- File/snapshot persistence through the internal ArtifactGateway; no direct changes to Knowledge approval fields.

## Excluded
Repairing V16, changing the technical truth policy, training large models, merging SEO strategy logic into the writer,
rewriting live ecommerce UI/CSS/product APIs, autonomous public publishing, Facebook Groups/browser bypass,
Zalo chatbot/CRM/customer inbox, unrestricted scraping, redesigning VPS/network infrastructure.

## Research deliverable
Map actual source/framework/lockfile versions; evaluate minimally invasive CMS adapter and LLM API integration.
Pin model/provider capability and maintain contract mocks. Do not infer hosting, API credentials or paid access from chat history.
Keep prompt templates versioned in Git, full articles/knowledge files in the approved Notion storage path.

## Acceptance
All applicable G01-G12, C01-C22 and P01-P08 require evidence.
The reference validator only checks IDs/hashes/shapes. Your quality suite must check source entailment, units,
negation and scope and detect factual assertions disguised as editorial/CTA text.
Use curated synthetic cases with known outcomes plus owner-approved real examples for human quality evaluation.
A status label alone never authorizes posting. Server resolves current role, approval, article/evidence revisions and feature flag.
Show a real rendered preview, not only a JSON response. At least one complete synthetic run produces a preview and mock
publication receipt; separately show a sandbox CMS DRAFT readback/reconciliation when scoped access is granted.
No exact text-match LLM tests: assert required facts, citation validity, exclusions and rubric outcomes; keep logs/model config.

## Delivery
Source with frontend/backend tests, reproducible build/lockfiles, non-root runtime, migrations+rollback,
Docker or equivalent startup, port config, environment example, health/capability endpoints,
OpenAPI/shared digest, provider fakes, unit/integration/browser/security tests with JUnit and screenshots,
source-bound sample preview, draft publication receipts, baseline-vs-candidate benchmark, SBOM/licenses,
artifact digest, known limitations and operator runbook.
No user-facing screen may claim LIVE/PUBLISHED when running the mock provider or awaiting storage confirmation.
