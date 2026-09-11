# State projection table — contract decision OPEN

Shared contract 1.0.0 is unmodified. Mapping is local adapter policy pending owner approval.

| Internal state | JobReceipt.status emitted | Notes |
|---|---|---|
| QUEUED | QUEUED | identity |
| LEASED | QUEUED | LEASED not in JobReceipt enum |
| RUNNING | RUNNING | identity |
| SUCCEEDED | SUCCEEDED | identity |
| FAILED | FAILED | or BUDGET_EXHAUSTED when error_code matches |
| CANCELLED | CANCELLED | identity |
| BLOCKED_INPUT | BLOCKED_INPUT | identity |

| Capabilities field | Emitted | Contract enum | Decision |
|---|---|---|---|
| service | content-workflow | seo-planning, content-workflow | OPEN: add runtime-orchestrator |

`acceptance_claimed=false` for this mapping.
