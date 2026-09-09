# V16.1 staging setup — 2026-09-04

Historical setup report, superseded by REMOTE_STAGING_EXECUTION_REPORT.md. Connectivity was restored and exactly one remote cycle subsequently completed with REMOTE_STAGING_PASS. The observations and config hash below describe the earlier blocked checkpoint, not current status.

Final status: `REMOTE_STAGING_BLOCKED`

Latest follow-up: dedicated V161-STAGING-TEST connection has staging-only Content access, only Read/Update content capabilities, and No user information. Insert, Comments and Agent capabilities are disabled. Fresh pytest: 103 passed in 2.67s; canonical hash matched again. Dedicated token was copied without displaying it, used only in a transient process, then removed in finally; clipboard cleared. Initial authenticated schema GET and exact seven-field type check succeeded. The subsequent schema GET in preflight raised a transport failure. No cycle launched and no PATCH sent. Independent TCP 443 connectivity probe also failed. Existing production integration was not reused or modified. Current blocker is connectivity, not permissions.

| Required report field | Result |
| --- | --- |
| test count/pass | 103 / 103 PASS (fresh full pytest suite) |
| staging target ID | See local staging-target.local.json, data_source_id; not the database/view UUID |
| 3 page IDs | 001: 3d1fbe3f…a0c8; 002: 3d1fbe3f…c27e; 003: 3d1fbe3f…10dd; exact ordered IDs in local config |
| apply count | 0 — NOT RUN |
| read-back result | Remote cycle NOT RUN; setup fetch confirmed all three pages and staging parents; dedicated API preflight stopped on transport error |
| second-run PATCH count | NOT RUN (not a demonstrated zero) |
| rollback count | 0 — NOT RUN; no harness updates to restore |
| final restoration result | NOT RUN |
| human-field write count | 0 |
| create count | Harness: 0; setup: one new private database with exactly 3 synthetic test pages |
| schema mutation count | Harness: 0; authorized setup: 6 added properties and 2 select options; existing Name title retained |
| production write count | 0 |
| artifact SHA256 | staging-target.local.json: 1c9534c964c72b0812f777cbdeb3a50890500b8f5b05fbeb7e62dbb70c4641c2; no remote-cycle artifacts exist |
| final status | REMOTE_STAGING_BLOCKED |

Fresh canonical plan reproduced locally in `.kaggle-deploy/v161-staging-chrome-baseline-20260904`; canonical SHA256 matched `af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399`.

The private database and its data source are named V161-STAGING-TEST. Read-only setup checks confirm the requested seven fields, RESOLVED and REVIEW_REQUIRED options, and three blank synthetic pages under the staging data source. Dedicated-token raw API schema/preflight and least-privilege access checks remain mandatory before execution.

Local strict validate_plan also passed against the existing production deny lists using the three actual staging page IDs: exactly three distinct non-production IDs, three UPDATE operations, zero CREATE operations, and zero unknown/human-owned PATCH fields.

No SQL, scheduler, Kaggle run, publication, production schema change, or Phase F performed. Do not recreate database/pages or change the now-correct permissions. Restore API connectivity and repeat read-only preflight using secure process-only credentials before executing the authorized single cycle into staging/artifacts/remote-cycle-001. No remote cycle has yet consumed that authorization. Do not infer PASS or replay verification from setup results.
