# INTERNAL_TAKEOVER — Vendor 4

Vendor vòng remediation dừng tại baseline R5. Việc dưới đây thuộc đội nội bộ; không yêu cầu vendor viết lại module.

## 1. G1 clean install
Input: Python with ensurepip/venv, network to install requirements.lock
Command: scripts/verify_local.sh
Done when: venv created, pip install -r requirements.lock, pip check, pytest exit 0, command receipt stored
Current: BLOCKED_ENVIRONMENT

## 2. Expected schema snapshot thật
Input: owner-signed mapping property ID → target data_source_id for Evidence Sources, Product Attributes, Knowledge Items, Canonical Knowledge; version + digest + provenance
Place: manifest expected_schema or expected_schema_path
Done when: pin loaded, drift vs live schema classified, no silent overwrite from provider GET
Current: only TEST_ONLY fixtures; official manifest has no owner pin

## 3. Live staging preflight (read-only)
Input: short-lived STAGING_NOTION_TOKEN out of band, STAGING_ENABLED=true, test_run_id
Command: python tools/staging_preflight.py --manifest STAGING_ACCESS_MANIFEST.json --read-only --output evidence/staging_preflight.json
Done when: schema+pagination+parent/target checks against pin; 401/403/429 classified; writes_attempted=0
Current: NOT_RUN

## 4. Relation remap
If live relations still point at production parents: BLOCKED_STAGING_RELATIONS. Do not bulk-repair. Owner remaps; vendor code already fail-closes.

## 5. Staging write / rollback
Separate opt-in. Allowlist fields only. No Status/Decision/Reviewer Note. Snapshot + mutation receipt + cleanup.

## 6. Deploy
Not in vendor scope. No production credential, no public effect.
