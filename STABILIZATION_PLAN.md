# THBISON-STABILIZATION-01

Frozen scope: Knowledge Factory + Content OS, TEST_ONLY, maximum two repair rounds.
Baseline candidate: 2c6a89e9abe5cce9252cc5e4f92b75f500001043, parent e1470d4d429519434c32296871825fc6f108f2d1.
Existing worktrees remain untouched. PR #11 is draft, head 601822789da365bd527f0eb0d8b427e713edbc99; it is historical component evidence, not the integrated candidate.

| ID | Class | Command/evidence and first failure | Cause | Repair scope | Verification |
|---|---|---|---|---|---|
| S01 | INTEGRATION | scripts/jobs/j2_verify_payload.py: two app-env paths missing from overlay | G1 patch omitted manifest refresh; modified blobs also need new overlay hashes | Regenerate exact integration overlay from staged files, preserve historical migration manifest | Existing verifier on final source |
| S02 | INPUT | V1/V2 OG tests reference absent .grok/skills/og and module AGENTS.md | Original resources and redistribution provenance unavailable | Bounded read-only review of project Notion and pinned provenance; no fabricated fixture | Explicit missing-input status; retain failing tests |
| S03 | INTEGRATION | vendor2/scripts/migration-plan.test.mjs expects no top-level SQL | Template assertion conflicts with legitimate Content OS 0002 migration | Preserve SQL and migrator; do not alter assertions under this job's rule | Run original test; retain exact conflict as blocker |
| S04 | EVIDENCE | Historical run 34550709921: CONTRACTOR_VERIFICATION_INCOMPLETE after tests/jobs passed | Full contractor gate includes unverified live obligations | Collect synthetic test results independently; preserve strict aggregate verdict | Separate source-only and strict full results; do not promote PARTIAL |
| S05 | ENVIRONMENT | Local Python subprocess initially WinError 5, then Git exit 128 | Sandbox/checkout ownership | Scoped per-process safe.directory for this checkout and approved subprocess execution | Repeat original verifier |
| S06 | INPUT | Existing J2 source-only inventory names three absent assets / six tests | Private inputs excluded from Git | Preserve established NOT_RUN inventory; do not reconstruct data | J2 JUnit and summary |

Round 1: refresh exact manifest, add candidate-bound evidence workflow. No algorithm, dependency, assertion, migration, contractor, production or Notion writes.
Round 2 only for reproducible blockers introduced/revealed by round 1 within this scope.
Final checks: source verifier; Knowledge source-only; V1/V2 script and source suites; V5/V6; actual-process E2E; dependency SHA and manifest accounting. Report each separately.
Notion reads: project 3cefbe3f22e681479dbbe30469cc7877; vendor1 handoff 3d7fbe3f22e681a99239f3bf58c65f8f; asset registry 3d6fbe3f22e681eda280ccf417574461. Registry describes older 8e03ae4 custody, not proof of OG provenance or current inputs.
DEFERRED: live Notion, production migration/deploy, scheduler, paid providers, training, refactor, template contract amendments without evidence-backed approval.
