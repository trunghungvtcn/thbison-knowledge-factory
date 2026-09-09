# V16 implementation — local NO_WRITE

## Verified

- Imported and reviewed the five supplied Python modules into `src/kf_pilot/v16`.
- Duplicate PLAN/SQL attachments have identical SHA256 hashes. SQL retained as reference only, not executed.
- Fixed unknown raw-condition handling, extra AST field rejection, mapping collision checks, and preservation of HOLD in the logical publication plan.
- Added explicit parsed AST input for the parser-change replay test, semantic required-field validation and former-signature alias support.
- 25 unit tests passed (17 existing and 8 new).
- Full V15 baseline: 70 canonical records and 102 publication mappings. Recorded local SHA256 fingerprints; these fingerprints alone are not independent remote checksum verification.
- Read live Notion Knowledge Items via connector: 114 existing records. Saved Decision, Reviewer Note, Status and page URL; all 70 V15 canonical mappings match live pages.
- Replayed migration against live decision/note snapshot. Notes preserved in decision bindings. No Notion writes.
- Reverse-row replay preserves entity/version IDs. A one-row AST change changes exactly one version, no entity IDs or page mappings.
- Logical publication plan: 70 UPDATE, 0 CREATE; 50 pending, 11 blocked by existing HOLD and 9 held for unresolved conditions.

## Outputs

`v16_migration/baseline-v15-live/` contains entities, versions, aliases, bindings, mappings, issues, baseline mappings/decisions, NO_WRITE plan and migration report.
`v16_migration/live_knowledge_snapshot.json` retains the live review-property snapshot. Discussion comments and full Notion audit history are not included.

## Not yet deployed remotely

The production Kaggle notebook remains V15. V16 has only been executed locally. No scheduler, farming, Supabase migration or remote V16 publication was activated.

Before remote publication:

1. Validate the SQL reference's entity/version ownership constraints (a semantic hash can be shared by different entities); do not run the supplied schema blindly.
2. Add and validate a compatible Notion schema. Current properties use `Knowledge ID`, `Claim Text`, `Applicability Scope`, `Reviewer Note`, and `Run ID`; the supplied V16 logical plan assumes different names plus new Entity/Version/Condition/System Status fields.
3. Convert the logical plan into typed Notion payloads; bind approvals to both entity and reviewed version and implement a safe decision pull.
4. Complete structured object-value extraction. The migration conservatively retains legacy claim text and numeric slots in object_value, so wording-only changes can still change semantic hashes.
5. Refresh live snapshots and backup system properties, run a Kaggle NO_WRITE commit, then obtain the V16 plan's phase-F approval before production mutation.

The original `VALIDATION_REPORT.md` describes a separate two-row fixture and is not evidence that this deployment is complete.
