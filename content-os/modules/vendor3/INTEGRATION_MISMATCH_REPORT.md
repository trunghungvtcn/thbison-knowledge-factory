# Integration mismatch report

contract_version: 1.0.0
CONTRACT_SHA256: fd3c1b6f1ec5461e7080c538e1c332d7af3098db32edd1565e1ae16933f951a8

1. JobReceipt.status omits LEASED. Local projection: LEASED → QUEUED. OWNER OPEN.
2. CapabilitiesReply.service omits runtime-orchestrator. Local emit: content-workflow. OWNER OPEN.
3. OpenAPI lists planning/content routes; SOW lease/reconcile routes are runtime additions; contract files unchanged.
4. Staging row counts in manifest are historical baselines; live counts NOT_RUN (BLOCKED_ACCESS).
5. Vendor 3 uses local SQLite ledger, not Notion knowledge DBs.

Contract files in this tree are not edited to make tests pass.
