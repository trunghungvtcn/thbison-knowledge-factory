# FIX_RESPONSE — FINAL (docs only, code_changed=false)

Source is the R2 baseline. No code change in this package.

## V6-R2-01 BLOCKER — CLOSED
Root cause: `Lab.run_reference_chain` invoked in-process simulators (`self.planning` … `self.cms`). Registry labels did not dispatch `binding.impl`.
Fix (R2, frozen): `run_chain` requires every hop via `registry.bindings[hop].impl` before side effects; traces record impl/vendor/transport/`verified_component`.
Reviewer repro: Trap now raises `ACTUAL_ADAPTER_WAS_CALLED:plan`. Spy positive controls and no-fallback tests passed.
Evidence: `evidence/reviewer/repro.txt`, `tests/test_dispatch.py` (inside frozen source.zip).
Remaining: spy/fake HTTP is not actual vendor integration.

## V6-R2-02 HIGH — CLOSED
Root cause: `if "weirdField" not in receipt: assert_valid(...)`.
Fix (R2, frozen): every PublicationReceipt is validated before `runtime.complete`; untrusted payload raises CONTRACT_INVALID; job not SUCCEEDED.
Reviewer: untrusted-payload test passed; bypass gone.
Evidence: `tests/test_int_matrix.py::test_int_22_untrusted_provider_payload`.

## V6-R2-03 HIGH — PARTIAL / OPEN
Not FIXED. R2 added a pinned synthetic protocol fixture, page budget, cursor-loop/missing-cursor fail-closed, and Retry-After via injected clock. That is mock protocol coverage only.
Reviewer: do not treat 21 fake tests as completed staging verification. `verified` stays false.
Open gaps handed to internal (see INTERNAL_TAKEOVER.md):
1. Missing row parent is silent.
2. Relation target uses `parent.page_id` only; no per-property `data_source_id` vs mapping.
3. `rel_rows` from relation pagination is unused; later-page targets are not checked.
4. Schema compare is by property name, not property ID; missing dest is skipped (`and dest`).
5. Fixture pin is a label, not a live schema snapshot.

Do not mark R2-03 CLOSED. Internal triage decides the follow-up job. No R3 from this vendor package.
