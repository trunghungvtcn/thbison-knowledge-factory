# V16.1 staging — operator guide

## Current status

`LOCAL_STAGING_HARNESS_PASS / REMOTE_STAGING_NOT_RUN`

The default CLI uses deterministic in-memory pages. Its UUIDs are test data, never remote target configuration. The HTTP staging adapter is implemented but has not been tested against a live staging database.

## Repeat local verification

From the `kaggle-pilot-jupyter` project directory, with the existing project Python dependencies available:

```powershell
python -m pytest -q
python staging/gate_staging_plan.py staging/synthetic_staging_plan.json
python staging/run_staging.py --output staging/artifacts/new-local-check
```

Always use a new output directory. Existing snapshots and rollback plans are never overwritten. Six artifacts plus an artifact hash manifest are written. Successful runs restore the before-image before exiting; the applied state is captured in `staging_readback.json`.

## Manual staging setup — no automation performs these changes

1. Create a separate Notion database/data source named with prefix `V161-STAGING`, never a copy containing production page IDs. Use a dedicated integration granted access only to this test target.
2. Set up the following fields manually. The harness will only read and validate schema; it will not create/rename fields or add select options.

| Property | Type | Existing options required |
|---|---|---|
| Name | title | — |
| Claim Text | rich_text | — |
| Run ID | rich_text | — |
| Condition Status | select | RESOLVED, plus any initial option used |
| System Status | select | REVIEW_REQUIRED, plus any initial option used |
| Decision | select | Optional human review field |
| Reviewer Note | rich_text | Optional human note field |

3. Pre-create exactly three empty test pages under that data source. Their title values must be exactly `V161-STAGING-SYNTH-001`, `V161-STAGING-SYNTH-002`, `V161-STAGING-SYNTH-003`. The harness has no CREATE/bootstrap route and does not change titles. Use simple text nodes for test system fields; unsupported before-image values cause a safe stop.
4. Obtain the **data-source UUID**, not the database-view ID. Record the three page UUIDs in the same 001/002/003 order.
5. Supply these process-only environment inputs locally or through a secret manager, never through chat or committed files:

| Variable | Required value |
|---|---|
| V161_ENV | STAGING |
| V161_STAGING_TARGET_ID | Dedicated staging data-source UUID |
| V161_STAGING_PAGE_IDS | JSON array containing the three staging page UUIDs in order |
| V161_STAGING_NOTION_TOKEN | Dedicated staging integration secret |

No existing Kaggle or production Notion token is used as a fallback. Configuring these values does not automatically execute anything.

## Explicit remote cycle after setup and authorization

Use secure local entry for the token, for example PowerShell `Read-Host -AsSecureString` or your secret manager. Do not put literal token values in command history. Invoke the command only when you intend to apply and restore the three test pages:

```powershell
python staging/run_staging.py --remote --output staging/artifacts/remote-cycle-001
```

The cycle snapshots all four system fields on all three pages and writes the rollback plan before any PATCH, performs three synthetic updates, reads back, re-applies the identical plan (zero PATCH expected), restores the before-images, and reads back independently. Human-owned fields are never included in any PATCH. There is no SQL, scheduler, schema update or production publication path.

Remove the process token after use. Never share artifact bundles without reviewing their contents: live before-images can include reviewer notes even though credentials are not included.

## Failure and concurrency

On an apply failure, the harness attempts rollback, including for writes whose responses were lost. If a page's system fields changed to a third value concurrently, recovery stops for that page and lists its UUID in `staging_rollback_report.json` rather than overwriting the edit. Read the saved before-image and rollback plan, resolve manually, and obtain direction before another run. Automatic rollback cannot be guaranteed when network access fails or other edits conflict.

To test review preservation manually, edit only a human field between fully completed staging cycles and invoke a new cycle into a new directory. That edit should appear unchanged in its before/readback/rollback artifacts. Do not edit system fields during a cycle.

Staging success does not authorize Phase F or publication of the 70 real records.
