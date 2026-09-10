# INTERNAL_TAKEOVER — Vendor 3

Đội nội bộ nhận source R5 không đổi. Việc còn lại không phải vòng vendor mới trừ khi có job scope riêng.

## Việc cần làm
1. G1: tạo venv sạch, `pip install -r requirements.lock`, `pip check`, `pytest`. Tiêu chí: exit 0, JUnit khớp.
2. Cung cấp expected_schema snapshot thật (version/digest/provenance + mapping property → data_source_id staging). Preflight thiếu pin = BLOCKED_OWNER_INPUT.
3. Quyết định contract: thêm LEASED vào JobReceipt và/hoặc service runtime-orchestrator, hoặc chấp nhận projection hiện tại. File: STATE_PROJECTION.md, CONTRACT_PROJECTION_PROPOSAL.md.
4. Live staging read-only: STAGING_NOTION_TOKEN + STAGING_ENABLED=true; xác minh parent relation; không ghi production.
5. Thay simulator bằng adapter Vendor 1/2/4 khi sẵn sàng; không đổi state machine.
6. Deploy/TLS/DNS production: job riêng, ngoài gói này.

## Lệnh kiểm chứng gợi ý
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.lock && .venv/bin/pip check
.venv/bin/pytest -ra --junitxml=evidence/junit.xml
PYTHONPATH=. python tools/staging_preflight.py --manifest STAGING_ACCESS_MANIFEST.json --read-only --output evidence/staging_preflight.json
```

## Tiêu chí xong (nội bộ)
- G1 sạch trên máy nội bộ
- Snapshot schema đã pin
- Owner quyết projection
- Live preflight (nếu cần) có run id / không secret trong log
