# Provider capability matrix

| Capability | Simulator | Native CMS |
|---|---|---|
| inspect | yes | BLOCKED_MISSING_INPUT |
| create private draft | yes | BLOCKED_MISSING_INPUT |
| lookup by external key | yes (can disable) | UNKNOWN |
| optimistic revision | yes | UNKNOWN |
| idempotency-key native | no (adapter ledger) | UNKNOWN — fail closed |
| media/signed URL | asset interface mock | BLOCKED_MISSING_INPUT |
| public publish | disabled | DENIED |
| LIVE | denied | DENIED |
