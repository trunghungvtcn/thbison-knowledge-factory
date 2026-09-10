# Your assignment: Vendor 2

Read `vendor_2/PROMPT.md` first.

# THBISON Content OS: two independent vendor workstreams

**Purpose:** hand off two bounded software modules while Knowledge V16 remains internal.
**State:** HANDOFF BASELINE, not implemented vendor applications, not a deployment.
Contract version: `1.0.0`. Proposal endpoints belong to THBISON adapters, NOT OpenSEO's native API.
Pilot: manual chain hoist / Vietnamese / Vietnam / Asia/Bangkok.

2. Vendor 2 reads `vendor_2/SOW.md`, `vendor_2/UX.md` and `vendor_2/PROMPT.md`.
3. Both read `contracts/BEHAVIOR.md`, `docs/ACCEPTANCE.md` and `docs/ACCEPTANCE_MATRIX.md`.
4. Owner supplies the identical contract bundle and pins its digest before work starts.
5. No vendor may edit the owner's tests, schemas, safety/publication rules or the other module to manufacture PASS.

## Included executable reference checks

Python 3.12+ proposed; this bundle is exercised on the interpreter recorded in `evidence/environment.json`.

```sh
python -m venv .venv
# Activate the environment with the command appropriate for your shell.
python -m pip install -r requirements-test.txt
python tools/verify_kit.py
python -m pytest -q --junitxml=reference-results.xml
python tools/demo_roundtrip.py
python tools/check_payload.py ContentBrief contracts/examples/ContentBrief.json
python tools/check_payload.py ArticlePackage contracts/examples/ArticlePackage.json --evidence contracts/examples/EvidenceBundle.json
```

These test the SHARED REFERENCE KIT, not a vendor implementation, an LLM's factual accuracy,
authentication infrastructure, durable concurrency or actual publication.
`ReferenceLedger` is deliberately in-memory. A production vendor must supply a transactional persistent ledger.
Reference fixture facts, SEO metrics, IDs and approvals are SYNTHETIC. They must never enter production knowledge.
The date 2030 in fixtures is a frozen simulation clock, not a schedule to execute.

## Boundaries

- Knowledge team: V16 repair, trusted evidence export, artifact gateway, actual VPS B operations and protected policy.
- Vendor 1: SEO adapter + topic/intent/clustering + planning backend + ContentBrief producer.
- Vendor 2: ONE Content OS UI, consumes Vendor 1 planning API, writing/evidence mapping, preview/approval,
  publishing adapter, social summary, content state machine.
- GitHub: code/release and CI. Notion: long-lived project data/files. VPS B: eventual execution and durable operational ledger.
- Mock development may start without V16 finishing. Real integration needs the internal evidence/artifact gateway.
- No production credentials, business decision CSVs, raw private corpus or old Git history are included.

## Delivery files

SOWs define ALL requirements. The 60-scenario matrix is normative for vendor acceptance.
The supplied reference tests are a starter, not that complete matrix.
Eight short assembly checks remain mandatory after the modules are integrated.
No claim of 'no testing ever again' is permitted; unchanged accepted suites are reused, not manually re-audited.
