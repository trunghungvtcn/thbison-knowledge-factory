# FIX_RESPONSE — Vendor 4 R5
acceptance_claimed: false
status: CHANGES_REQUIRED

## Expected schema pin vs provider schema — FIXED_VERIFIED
Root cause: expected_target built only from provider GET schema; expected_schema in manifest ignored.
Fix: resolve_expected_snapshot + compare_schema_to_expected (id, property id/type, relation destination). Target parent checked against pin, not provider dest.
REPRO wrong_target: SCHEMA_DRIFT / CHANGES_REQUIRED, exit 0 (was PREFLIGHT_MOCK_OK).
Positive: expected B / provider B / target B -> PREFLIGHT_MOCK_OK.
Missing pin -> BLOCKED_OWNER_INPUT.

## Prior R4 gates kept
wrong allowlist dest, truncated, restart tests unchanged in intent.

## G1 BLOCKED_ENVIRONMENT
## G7 NOT_RUN
