# J3 ACCEPTANCE

acceptance_claimed: false

Pass only if all are true:

- [ ] Transport allow-list is enforced before Projector.project
- [ ] Check is not "class name starts with Fake" and not "has .calls"
- [ ] reserve_budget / record_attempt / finalize / project errors cannot yield LOCAL_SHADOW_COMPLETE
- [ ] Replay reads ledger state; IDEMPOTENT_HIT on a non-terminal job is not reported as complete
- [ ] J1 commit SHA and J1 input hash are separate fields; same for J2
- [ ] Both commit SHA and input hash are bound into request digest and receipt
- [ ] Missing contractor install is a hard failure of the acceptance command, not pytest.importorskip PASS
- [ ] Only contractor_bridge + J3 tests/docs changed
- [ ] Issue #2 is the mailbox; issue #5 only points at #2
- [ ] READY_FOR_REVIEW comment cites HEAD, command, exit code, JUnit

Fail if LOCAL_SHADOW_COMPLETE is returned after a failed ledger or project envelope.
