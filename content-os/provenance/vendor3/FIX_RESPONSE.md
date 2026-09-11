# FIX_RESPONSE — Vendor 3 R5

acceptance_claimed: false

| Issue | Status | Root cause | Change | Before | After |
|---|---|---|---|---|---|
| Expected schema dest not pinned | FIXED_VERIFIED | fetch_schema ignored relation destination; collect used provider mapping | compare dest to expected_schema; READ_OK requires pin | REPRO READ_OK | SCHEMA_DRIFT provider=ds-a expected=ds-b |
| Missing pin treated verified | FIXED_VERIFIED | no owner snapshot | BLOCKED_OWNER_INPUT | could READ_OK | not verified |
| Projection | BLOCKED_OWNER_DECISION | enum | proposal only | OPEN | OPEN |
| G1 | BLOCKED_ENVIRONMENT | ensurepip | evidence | blocked | blocked |
| G7 | BLOCKED_ACCESS | no token | | | |
