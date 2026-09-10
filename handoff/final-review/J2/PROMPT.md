# J2 PROMPT — final remediation

JOB_ID=J2
MAILBOX=https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/4
PUBLISHED_HEAD=5e6161914f519403059ce13a1568d58ac7162f28
PR=https://github.com/trunghungvtcn/thbison-knowledge-factory/pull/8
CORE=3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b

This kit is a GitHub-required guidance pack. It is not offline-complete.

Issue #4 already published HEAD `5e6161914f519403059ce13a1568d58ac7162f28`.
Use that SHA. Do not mark J2 UNPUBLISHED.

## Allowed trees

- environment / runner config for source-only verification
- `.github/workflows/verify.yml`
- `scripts/jobs/j2_*`
- `docs/jobs/J2*`

## Required final fix

1. Source-only suite may be split from suites that need private / gitignored assets.
2. Every deselected test must appear in the receipt with: nodeid, missing input, status `BLOCKED_INPUT` or `NOT_RUN`.
3. Do not claim full-suite PASS from a subset.
4. Publish HEAD, exact command, exit code, JUnit path, and the number of tests actually executed.
5. Do not change algorithms. Do not change contractor CI.

## Out of scope

Contractor repo, algorithm changes, merge, deploy, corpus publication.
