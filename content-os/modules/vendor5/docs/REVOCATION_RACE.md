# Revocation race policy

Approval and evidence are loaded from the authoritative store immediately before dispatch. Client `status=APPROVED` is ignored.

If approval is revoked after admission but before provider call: no new create.

If revoke happens while a create is in flight and the provider accepted the draft: persist UNKNOWN/created draft, record race on the ledger, quarantine via reconcile. Adapter does not publish or delete a real CMS article. Rollback applies only to own test_run_id drafts in the simulator.
