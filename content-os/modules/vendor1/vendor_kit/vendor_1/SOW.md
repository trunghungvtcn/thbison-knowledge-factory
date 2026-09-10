# Vendor 1: OpenSEO adapter and planning backend

## Outcome
A runnable service that turns a project goal + seed topics + existing-page inventory into traceable
SEO observations, topic clusters, a prioritized plan and ContentBrief revisions consumed unchanged by Vendor 2.
It must work with synthetic providers while Knowledge V16 is still being repaired.

## Research that must lead to implementation
Inspect upstream every-app/open-seo and the current official MCP/API documentation. Record exact upstream commit,
license, supported tool/schema versions, authentication flow and provider costs. Preserve required notices.
Prefer an adapter to OpenSEO rather than rewriting its keyword/SERP engine or copying its full application.
Do not hardcode tool names remembered from an old README; discover supported tools and pin capability fixtures.
Our /v1/planning endpoints are wrapper routes, not claims about upstream.
Compare baseline vs a measured improvement (cache, provider batching, bounded parallelism, duplicate elimination).
No paper-only architecture deliverable; ship the service, tests and an actual measured report.

## In scope
- Locale-aware research VN/vi, keyword metrics, SERP summaries and provenance, stale/missing/synthetic handling.
- Existing-page matching, duplicate/cannibalization recommendations, intent clusters with editable rationale.
- Prioritization and a proposed editorial calendar, not an automatic publication scheduler.
- Versioned briefs: target audience/questions/outline/product refs/evidence requirements/constraints.
- Read API for the Content OS planning screen; optimistic revision checks for user edits.
- Provider mode switches, caching, reservations/budgets, cancellation, deadlines and bounded retry.
- Consumer tests proving Vendor 2 can use the actual ContentBrief output; use golden data and mutation cases.
- Minimal SEO performance feedback ingestion, treated as demand/content feedback, never labels of technical truth.

## Excluded
Knowledge framing/repair/training, approval of technical claims, writing/publishing articles, redesign of thbison.vn,
CMS credentials, global Notion schema changes, another dashboard shell, autonomous model/code self-modification,
backlink campaigns or broader SEO-suite reimplementation.
No requirement to scrape competitors' full copyrighted article text for reuse.

## Source requirements
Clear provider/normalizer/planner/cache/budget/transport boundaries. Centralized configuration, no hidden global state.
Lock dependencies and language/runtime versions. App may follow the upstream implementation stack after inspection;
external interoperability is HTTP JSON and the shared contract, not same programming language.
Source tests must not need live API keys. No forced GPU/Colab dependency for API requests.
Ship Dockerfile or equally reproducible build with non-root runtime, health/capability endpoints and clean dependency install.

## Acceptance
All applicable G01-G12, S01-S18 and P01-P08 in the shared matrix must have evidence or an explicit required external blocker.
Application tests MUST exercise actual vendor code, not only the shared reference oracle.
Record source baseline and final commit, raw benchmark samples, provider request counts, cost attribution, cache hit behavior.
Public contract fixtures are necessary but insufficient: add parameterized/held-out variations so code cannot return a fixture blindly.
Receipt status separates OFFLINE_VERIFIED from ADAPTER_VERIFIED and INTEGRATED_CANARY_PASS.
A real upstream read probe is required for ADAPTER_VERIFIED when the owner provides scoped credentials/budget.
No credentials -> mark that gate NOT_RUN_EXTERNAL, deliver all independent source work.

## Delivery
Full private source and history of this work, lockfiles, setup/rollback guide, environment-variable example with no secrets,
OpenAPI and contract hash, sanitized recorded protocol fixtures, tests/JUnit and test ID mapping, security/dependency scan,
license inventory/SBOM, exact artifact digest, baseline-vs-candidate report, list of unimplemented/not-tested paths.
Ship adapter tests and documented run commands; do not ask the integrator to invent endpoints or rename fields later.
