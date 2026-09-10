# J3 ACCEPTANCE

acceptance_claimed: false
reviewed_sha: 9a7d09375bf242f3cf89b9e2d556192a12e8b830
mailbox: https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/2
pointer: https://github.com/trunghungvtcn/thbison-knowledge-factory/issues/5

Reviewer checks only these items. One pass.

## Must pass

- [ ] Transport allow-list is enforced **before** `Projector.project`
- [ ] Check is not "class name starts with Fake" and not "has `.calls`"
- [ ] `reserve_budget` / `record_attempt` / `finalize` / `project` errors cannot yield `LOCAL_SHADOW_COMPLETE`
- [ ] Replay reads ledger state; `IDEMPOTENT_HIT` on a non-terminal job is not reported as complete
- [ ] J1 commit SHA and J1 input hash are separate fields; same for J2
- [ ] Both commit SHA and input hash are bound into request digest and receipt
- [ ] A hex string is not treated as HASH_VERIFIED merely by existing
- [ ] Missing J2 env/input hash (none published on issue #4 beyond HEAD) is BLOCKED_INPUT, not invented
- [ ] Missing contractor install is a hard failure of the acceptance command, not `pytest.importorskip` PASS
- [ ] Only `src/kf_pilot/contractor_bridge/` + `tests/jobs/test_j3_*` + `docs/jobs/J3*` changed
- [ ] Issue #2 is the mailbox; issue #5 only points at #2
- [ ] READY_FOR_REVIEW comment cites HEAD, command, exit code, JUnit

## Must fail the review

- `LOCAL_SHADOW_COMPLETE` after a failed ledger or project envelope
- Transport allow-list implemented via `Fake*` name or `.calls`
- `importorskip` on the acceptance path
- Contractor repo edited
- Work executed from issue #5 as if it were the mailbox
