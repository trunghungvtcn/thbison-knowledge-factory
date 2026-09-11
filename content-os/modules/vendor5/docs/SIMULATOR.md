# Simulator

In-memory + durable ledger. Faults: none, timeout-after-accept, timeout, unavailable (5xx), rate_limited (429), schema_drift, delayed, 4xx.

State: drafts by provider_record_id and external key, revision counter, public=false, test_run_id.

Does not implement a background scheduler (Vendor 3 ownership). Retry loops are bounded in the adapter call stack.
