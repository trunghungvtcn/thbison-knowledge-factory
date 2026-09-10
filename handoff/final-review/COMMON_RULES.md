# COMMON RULES

1. Work only inside the job scope listed in that job's PROMPT.md.
2. Fork from the Core baseline `3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b` or from the named reviewed SHA. Do not rewrite history pins to go green.
3. Contractor repo `trunghungvtcn/pipeline-lab-contractor-m1-m5` @ `afac091e60bb6c8a0f0630964e43f5e80951267c` is out of scope. Do not edit it. Keep existing PASS gates.
4. Mode is TEST_ONLY / LOCAL_SHADOW / source-only as specified. No production writes. No live Notion. No paid models. No scheduler.
5. Missing input is BLOCKED_INPUT or NOT_RUN. Do not invent SHA pins, corpus, or inventory rows.
6. Distinguish commit SHA from content hash. A 40-char hex string is not HASH_VERIFIED by existing.
7. Subset results must not be labelled full-suite PASS.
8. Do not merge. Do not close issues to hide history. Issue #5 stays open as a pointer to #2.
9. One fix pass, then reviewer. READY_FOR_REVIEW != ACCEPTED. acceptance_claimed=false unless the owner says otherwise.
10. Report honestly: command, HEAD, exit code, JUnit path, counts, holds.
