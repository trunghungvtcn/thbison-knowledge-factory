# J3 LOCAL_SHADOW contractor adapter

JOB_ID=J3
BRANCH=jobs/j3-contractor-adapter-20260910
REVIEWED_SHA=9a7d09375bf242f3cf89b9e2d556192a12e8b830
CONTRACTOR_BASELINE=afac091e60bb6c8a0f0630964e43f5e80951267c
MODE=LOCAL_SHADOW
acceptance_claimed=false

## Final remediation (on reviewed SHA)

- Transport allow-list is `LOCAL_SHADOW_ALLOWED is True`, checked before `Projector.project`.
- Class-name prefix `Fake` and attribute `calls` are not used as the allow-list.
- `reserve_budget`, `record_attempt`, `finalize`, and `project` errors cannot return `LOCAL_SHADOW_COMPLETE`.
- Replay calls `JobLedger.get` first. `IDEMPOTENT_HIT` on a non-terminal state is `IDEMPOTENT_HIT_NON_TERMINAL`, not complete.
- J1/J2 **commit SHA** and **input hash** are separate. Format-ok is not verified. Both are bound into request digest and receipt. Input hashes stay `*_input_verified=false` until an inventory digest is published.
- Missing contractor packages fail the acceptance command. Tests do not `importorskip`.

## Run

```bash
git clone https://github.com/trunghungvtcn/pipeline-lab-contractor-m1-m5.git contractor
git -C contractor checkout afac091e60bb6c8a0f0630964e43f5e80951267c
export CONTRACTOR_ROOT="$PWD/contractor"
export PYTHONPATH="$CONTRACTOR_ROOT/m1_locator/src:$CONTRACTOR_ROOT/m2_asset_store/src:$CONTRACTOR_ROOT/m3_job_ledger/src:$CONTRACTOR_ROOT/m4_notion_projection/src:$PWD/src"
python -m pytest tests/jobs/test_j3_mapping.py tests/jobs/test_j3_adapter_shadow.py tests/jobs/test_j3_holds.py tests/jobs/test_j3_contractor_required.py -q --junitxml=docs/jobs/J3-junit.xml
```

Missing CONTRACTOR_ROOT / packages → command fails (not skip-pass).

## Out of scope

merge, deploy, scheduler, live Notion, paid models, contractor edits, GitHub Release.
