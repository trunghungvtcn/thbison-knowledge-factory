# Repair and architecture alignment report

## Scope

- Job: `MCH-MIGRATE-KAGGLE-GITHUB-001`
- Baseline: `8865b1031bf5aa2a91df7ad8c8a6e11b3b1ee38f`
- Review branch: `fix/migration-architecture-alignment`
- Source repository remains the code source-of-truth; data assets remain outside Git.

## Implemented

- Restored cumulative V16.2–V16.6 source, recovery documentation, deterministic fixtures, and verification packs needed to reproduce the historical test suite.
- Removed the reviewed `config/manual_decisions.csv` from the current tree and registered its external copy by SHA-256.
- Added a fail-closed `TEST_ONLY` runtime contract with full commit/input pinning, retry and timeout budgets, allowed-output checks, idempotency ledger, and no production writes.
- Added pinned GitHub Actions verification, Python 3.12 metadata, dependency validation, compilation, source-only offline tests, payload verification, and a source archive artifact.
- Added migration manifest verification, Git text normalization, data/cache exclusions, and secret-pattern scanning.

## Verification evidence

- Python: 3.12.14 in an isolated environment.
- Dependency check: PASS.
- Compile: PASS.
- Historical/source suite: 401 passed; 4 contract tests were excluded locally because this managed Windows sandbox blocks child `git` execution. They remain enabled in Linux CI.
- Secret-pattern scan of the candidate tracked tree: no matches for the tested high-confidence token/private-key patterns. This is evidence, not a claim that secret detection is exhaustive.
- No tracked file exceeds 10 MiB.

## Explicit non-claims

- `runtime_deployed=false`
- `scheduler_enabled=false`
- `production_knowledge_writes=false`
- `model_training=NOT_RUN`
- `model_improvement=NOT_EVALUATED`

## Residual risks

- The removed decisions CSV exists in the pre-migration Git history. The repository was made private; history was not rewritten because that would be destructive.
- External data and Notion custody must be verified independently from the Git source receipt.
- Merge and production deployment require separate approval.
