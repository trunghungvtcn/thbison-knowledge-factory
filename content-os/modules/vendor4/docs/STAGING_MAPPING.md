# Staging mapping (no live access)

Pin revisions via env: STAGING_SOURCE_REVISION, STAGING_SCHEMA_REVISION.

| Logical name | data_source_id | access |
|---|---|---|
| Evidence Sources | c80fbe3f-22e6-8329-9dd6-875fb67a3755 | READ in source; writes only if operator confirms parent is staging |
| Product Attributes | e51fbe3f-22e6-82e8-8831-07a909bdba1a | same |
| Knowledge Items | 367fbe3f-22e6-82cf-9f1f-0762f4850df9 | same; do not follow production relations |
| Canonical Knowledge | d22fbe3f-22e6-82fa-944c-076af76d5960 | same |

Expected row counts in the manifest are historical baselines, not invariants.

Preflight status in this package: BLOCKED_ACCESS (no token).
