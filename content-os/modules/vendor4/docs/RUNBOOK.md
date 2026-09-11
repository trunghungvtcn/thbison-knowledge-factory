# Runbook

1. Copy `.env.example` and set TEST_RUN_ID.
2. `pip install -r requirements.txt && pytest -q`
3. `uvicorn app.main:app --port 8080`
4. Query with Bearer token and X-Contract-Version 1.0.0
5. For staging (operator): set STAGING_NOTION_TOKEN, pin STAGING_SOURCE_REVISION, never ALLOW_PRODUCTION=true
6. Cleanup: discard TEST_RUN_ID namespace; do not write Status/Decision/Reviewer Note
