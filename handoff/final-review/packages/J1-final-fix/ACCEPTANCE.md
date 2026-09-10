# J1 ACCEPTANCE

acceptance_claimed: false
reviewed_sha: b9e291fb84ddf99a6e6dd662ae122f39326f4d41
mailbox: https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/3

Reviewer checks only these items. One pass.

## Must pass

- [ ] Strict mode: missing file → exit code ≠ 0
- [ ] Strict mode: hash mismatch → exit code ≠ 0
- [ ] Inventory / report mode still produces a listing without rewriting source data
- [ ] Receipt or report labels PRESENT separately from HASH_VERIFIED
- [ ] Present-without-digest is not labelled HASH_VERIFIED
- [ ] Three hashes published: audited source SHA, tool SHA, inventory content hash
- [ ] Reproduction command for each hash is documented against the exact bytes
- [ ] Historical pins and recovered data files are unchanged (byte-identical on watched inputs)
- [ ] Tests target only the rules above
- [ ] Missing input is reported honestly (BLOCKED_INPUT / MISSING / MISSING_EXTERNAL), not a silent skip that is then called PASS
- [ ] Diff limited to `scripts/jobs/j1_*`, `tests/jobs/test_j1_*`, `docs/jobs/J1*`
- [ ] READY_FOR_REVIEW posted on issue #3 with HEAD, command, exit code, JUnit

## Must fail the review

- Any historical pin or recovered file rewritten to go green
- Strict mode still exits 0 on missing or mismatch
- PRESENT and HASH_VERIFIED collapsed into a single `OK`
- Private corpus or custody zip uploaded to GitHub
