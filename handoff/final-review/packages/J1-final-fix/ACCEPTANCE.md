# J1 ACCEPTANCE

acceptance_claimed: false

Pass only if all are true:

- [ ] Strict mode: missing file → exit != 0
- [ ] Strict mode: hash mismatch → exit != 0
- [ ] Inventory mode still produces a report without rewriting source data
- [ ] Receipt or report labels PRESENT separately from HASH_VERIFIED
- [ ] Three hashes published: audited source SHA, tool SHA, inventory content hash
- [ ] Reproduction command for each hash is documented against the exact bytes
- [ ] Historical pins and recovered data files are unchanged
- [ ] Tests target only the rules above
- [ ] Missing input is BLOCKED_INPUT, not a silent skip that is then called PASS
- [ ] Scope limited to j1 scripts/tests/docs
- [ ] READY_FOR_REVIEW posted on issue #3 with HEAD, command, exit code, JUnit

Fail if any historical pin was rewritten to go green.
