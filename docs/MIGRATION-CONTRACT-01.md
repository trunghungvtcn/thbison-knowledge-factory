# MIGRATION-CONTRACT-01

User authorized resolving OG provenance and the reproduced migration contract conflict on 2026-09-11. This is the explicit contract amendment deferred by THBISON-STABILIZATION-01, not permission to hide migrations or weaken checks.

Baseline: 5eef0f206ff40f453dcc0871c113725b84fb791a.
Evidence: Linux run 34557244257, vendor2-scripts.xml; local migration-plan.test.mjs: 6 PASS / 1 FAIL. The test titled 'the auth schema ships outside the globbed directory' expected all top-level migrations to be absent, even though Content OS requires 0002_content_os.sql.

Required behavior:
1. Auth OFF: migrations/auth/0001_auth.sql remains present outside default top-level discovery; migrations/0001_auth.sql must be absent.
2. The integrated V2 tree must discover exactly 0002_content_os.sql as the initial top-level application migration. An unexpected SQL file fails this contract and requires explicit review.
3. Once 0002_content_os.sql is recorded as applied, it is not pending again.
4. Preserve existing ordering and basename-idempotency tests.
5. Preserve migration-plan.mjs, migrate.mjs, src/lib/db.ts, SQL bytes and historical migration receipts.

The existing test retains its identity and now asserts auth exclusion, exact application migration membership and already-applied exclusion. Collection count is unchanged. This replaces an incorrect empty-template assumption with the integrated application contract; no test is skipped.

Unit discovery/idempotency is not proof of PostgreSQL execution. Previous Neon evidence remains historical at RC2; a final-source database receipt is a separate gate. No database writes are authorized by this amendment.
