# V16.2 Data-Quality Remediation + Phase F Readiness Pack

This pack continues from the verified V16.1 checkpoint:

- V16.1 production canonical baseline SHA256: `af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399`
- Kaggle remote NO_WRITE v2: PASS
- Notion remote staging: `REMOTE_STAGING_PASS`
- 103/103 tests passed immediately before the remote staging cycle
- Production writes remain 0
- Phase F remains NOT AUTHORIZED

## Objective

Implement V16.2 as a **NO_WRITE remediation/readiness layer** that accounts for all 79 known data-quality issue entries, resolves only evidence-backed deterministic cases, preserves ambiguous cases as HOLD/NEEDS_REVIEW, and produces an eligible production subset plus a Phase F canary plan without executing it.

## Start here

Paste `PROMPT_CODEX_DEPLOY_V162_REMEDIATION.md` into the code agent working in the verified repository.

The included Python gates are independent fail-closed validators for the remediation ledger and Phase F readiness summary. They do not connect to Notion, Kaggle, SQL, or any scheduler.
