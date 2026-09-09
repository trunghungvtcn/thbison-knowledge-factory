# Safety scope

V16.2 is NO_WRITE for production.

Allowed: local computation, read-only reconciliation, deterministic remediation, tests, artifact generation, canary planning.

Not allowed: production Notion mutation, SQL execution, scheduler enablement, Kaggle rerun/upload, production schema mutation, Phase F canary execution.

Human-owned fields remain immutable to system payloads: Decision, Reviewer Note, Reviewed Entity ID, Reviewed Version ID.
