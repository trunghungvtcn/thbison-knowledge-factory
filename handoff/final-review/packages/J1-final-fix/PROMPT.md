# J1 PROMPT — final remediation

JOB_ID=J1
MAILBOX=https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/3
REVIEWED_SHA=b9e291fb84ddf99a6e6dd662ae122f39326f4d41
PR=https://github.com/trunghungvtcn/thbison-knowledge-factory/pull/7
CORE=3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b

This kit is a GitHub-required guidance pack. It is not offline-complete.

## Allowed trees

- `scripts/jobs/j1_*`
- `tests/jobs/test_j1_*`
- `docs/jobs/J1*`

## Required final fix

1. Add a **strict** mode: missing path or hash mismatch exits non-zero. Keep the existing inventory / report mode for listing.
2. Distinguish **PRESENT** (path exists) from **HASH_VERIFIED** (bytes match the published digest on the exact file).
3. Separate three hashes and publish how to reproduce each on the same bytes:
   - audited source SHA (git commit of the inventory code)
   - tool SHA (git blob or file hash of the auditor script)
   - inventory content hash (canonical inventory document)
4. Do not edit historical pins or original recovered data to make tests green.
5. Tests cover only those three rules. If an input is absent, report BLOCKED_INPUT. Do not fabricate rows.

## Out of scope

Merge, deploy, scheduler, Notion writes, paid models, contractor repo, private corpus upload.
