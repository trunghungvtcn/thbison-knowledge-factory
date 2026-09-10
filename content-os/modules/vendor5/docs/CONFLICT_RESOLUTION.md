# Conflict-resolution runbook

1. Same Idempotency-Key + same canonical payload → return stored receipt (CMS-09).
2. Same key + different payload → 409 IDEMPOTENCY_CONFLICT (CMS-10).
3. Concurrent create with same external key → one draft (CMS-11).
4. Timeout after accept → lookup; do not create again (CMS-12).
5. Stale expectedRevision → STALE_REVISION; keep human body (CMS-16).
6. Schema drift → SCHEMA_DRIFT fail closed (CMS-25).
