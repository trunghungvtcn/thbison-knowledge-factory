# J2 ACCEPTANCE

acceptance_claimed: false

Pass only if all are true:

- [ ] Source-only suite is identifiable and does not require private assets
- [ ] Every deselected test has nodeid + missing input + BLOCKED_INPUT or NOT_RUN in the receipt
- [ ] Report does not say full-suite PASS when tests were deselected
- [ ] HEAD `5e6161914f519403059ce13a1568d58ac7162f28` (or a later reviewed SHA on the same job branch) is cited
- [ ] Command, exit code, JUnit, and executed-count are in the issue #4 comment
- [ ] No algorithm or contractor CI edits
- [ ] Scope limited to J2 trees

Fail if subset green is labelled as full suite.
