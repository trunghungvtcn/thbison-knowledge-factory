# Source acceptance and measurable optimization

## Levels (do not collapse to one PASS)

- KIT_SELF_TEST_PASS: the supplied reference schemas/oracles run. Not vendor acceptance.
- OFFLINE_VERIFIED: vendor source, full own tests, applicable matrix scenarios and consumer/provider replays pass using mocks.
- ADAPTER_VERIFIED: additionally, exact provider protocol/auth/capabilities pass on scoped real/sandbox systems.
- INTEGRATION_READY: both vendors' accepted artifacts share a contract and no required gate is open; internal ports ready.
- INTEGRATED_CANARY_PASS: eight assembly checks pass on actual selected environment.
- PRODUCTION_ENABLED: separate operator authorization. Never inferred from any previous label.

Deliverable receipt fields: module, source commit/tree hash, contract SHA256, artifact/container digest,
upstream/provider/tool versions, lockfile hash, test fixture hash, environment, applicable test IDs and
passed/failed/skipped/not_run counts, JUnit/log hashes, sandbox evidence IDs, known defects, benchmark samples,
code diff summary, real_paid_calls and public_publications counts. No token or signed download URL in receipts.
Only the maintainer-controlled CI/acceptance runner can grant a delivery gate, not the vendor's model.

## Mandatory engineering gates

Clean checkout -> reproducible dependency install -> build/type/compile -> lint warnings report ->
unit/integration/contract/browser/security -> artifact build -> exact-artifact tests and checksum -> receipt.
No required scenario skipped/xfail/deselected without a visible accepted exclusion. No overwritten golden data.
No reachable exploitable critical/high vulnerability in delivered paths; retain documented justification for false positives.
Vulnerability scanning and `pip check`/package install are different checks; supply both applicable tools, not one mislabeled as both.
Secrets never enter repository, image or frontend bundle. No public forks with private inputs; upstream license preserved.
Two modules must use each other's actual contract outputs in a replay test, not two unrelated mocks with similar field names.
A fixture-driven smoke test is not semantic evaluation, concurrency testing or live credentials validation.

## Performance targets: proposed fixed pilot benchmark, not current results

Freeze before vendor implementation. Reference environment for benchmark: 2 vCPU / 4 GiB RAM per backend container,
external LLM/SEO latency excluded and reported separately; no GPU. Use the same hardware/input/versions for before/after.
- G/P job admission: 100 requests, concurrency 5; p95 <= 1000 ms excluding provider calls.
- Cached brief retrieval: 100 requests after warmup; p95 <= 500 ms.
- Cached rendered preview for a 10,000-character fixture: p95 <= 2000 ms, excluding new generation.
- 20 concurrent repeats of the SAME logical job: one admission and at most one external logical publication.
- Peak memory, cold startup, provider requests/tokens/cost and cache hit rate: measured, no invented zeroes.
- Optimization target: >=15% improvement in one declared metric vs the first working baseline, with all correctness gates intact.
  If unattained, mark optimization NOT_MET/NO_IMPROVEMENT; do not fudge benchmark or weaken correctness.
Production VPS capacity is not known or promised by this reference benchmark.

Content quality: freeze rubric and an owner-controlled hold-out set. All known unsupported safety/legal assertions and
fabricated citations in that set must be caught; this is a finite observed result, not a guarantee of universal truth.
Review title/intent coverage, source entailment, citation scope, Vietnamese readability and duplication separately from SEO metrics.
Missing reviewer labels cannot be replaced by the same model grading its own outputs and called independent evaluation.

## Delivery contract / responsibility

Vendor is responsible for fixing interface/behavior mismatches against the frozen scope before integration acceptance.
Scope change, new provider capability or new platform is a separately approved change, not an unlimited free repair loop.
No proprietary handoff-only binaries: include editable source, build scripts, tests, dependency license list and reproducible artifact.
No third-party team may change master schemas, tests, safety policy or approval authority without explicit owner review.
Payment/acceptance milestones can map to D1 runnable skeleton, D3 full isolated evidence, D4 protocol-tested release,
and D6 integrated canary. Financial/contract terms are for the parties to agree, not set by this technical kit.

References verified for this handoff (2026-09-10):
- https://openseo.so/features/mcp
- https://openseo.so/docs/skills/keyword-research
- https://docs.pact.io/faq
- https://docs.pact.io/
- https://developers.notion.com/guides/data-apis/uploading-small-files
- https://developers.notion.com/reference/request-limits
- https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
