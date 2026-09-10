# Runbook — Vendor 3 Runtime

## Lab start
```
python -m pytest tests/test_acceptance.py
# optional
uvicorn app.api:app --port 8080
docker compose up --build
```

## Flags
- `APP_MODE=MOCK` default
- `ALLOW_PRODUCTION=false`
- `ALLOW_PUBLIC_EFFECTS=false`
- Outbound network treated as blocked in lab (`egress_blocked=True`)

## Restart
SQLite WAL file is the durable ledger. Restart loads existing jobs. Terminal jobs stay terminal.

## Rollback
Delete the SQLite file or restore a file copy taken before a test run. Compensating unpublish is out of scope.

## Staging
Requires out-of-band short-lived Notion credential. Pin revisions from STAGING_ACCESS_MANIFEST.json. Every write needs TEST_RUN_ID. Cleanup after run.
