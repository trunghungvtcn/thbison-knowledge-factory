# Vendor 6 changelog

## R2
- V6-R2-01: run_chain dispatches exclusively via registry.impl; traces record impl class, vendor, transport, verified_component=false for spies/fake HTTP. Trap adapters raise. MIXED/ACTUAL no simulator fallback.
- V6-R2-02: PublicationReceipt always schema-validated before runtime.complete; schema_drift cannot skip the guard; job not SUCCEEDED.
- V6-R2-03: preflight uses pinned protocol fixture; property id/type/relation mapping; row parent DS; allowlist; bounded pagination; cursor loop/missing cursor fail-closed; Retry-After via injected clock.

## R1
Contract-valid simulators, adapter registry labels, fake staging transport (insufficient protocol).
