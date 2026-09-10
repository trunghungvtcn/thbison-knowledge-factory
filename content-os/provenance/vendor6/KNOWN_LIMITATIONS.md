# Known limitations — FINAL

code_changed: false  
acceptance_claimed: false

- G1 clean install: BLOCKED_ENVIRONMENT (ensurepip / isolated venv not verified). Reviewer also used a preinstalled environment. 71 PASS is not a clean-install PASS.
- Actual V1–V5 deployed processes: NOT_RUN. INT-26 skipped. SpyAdapter and FakeHttpTransport are mock protocol; traces set verified_component=false.
- Vendor 5 candidate referenced outside this kit is not accepted here and was not wired as a pinned version.
- Live staging: BLOCKED_ACCESS (no out-of-band token in package; no live call). Fake preflight verified=false.
- V6-R2-03 PARTIAL/OPEN: remaining protocol gaps listed in INTERNAL_TAKEOVER.md. 21 fake staging tests do not complete staging verification.
- INT-27 paired benchmark: NOT_RUN (no paired baseline/candidate timings).
- V4 ContentBrief→query mapping remains PROPOSED.
- Contract 1.0.0 frozen; no schema relaxation.
