# Vendor 5 Fix R2

- HIGH: bind policy_version across ApprovalRecord, ArticlePackage, EvidenceBundle before DRY_RUN and mutations.
- Also bind data_class, project_id, bundle_id remaining contract links (no schema field additions).
- verify_local.sh fail-closed: every gate exit code propagated; no VERIFY_LOCAL_OK on failure.
- Wheelhouse: rpds-py cp310+cp311+cp312 manylinux x86_64. Supported CPython 3.10-3.12.
- SQLite ledger init retries on lock (two-process create).
