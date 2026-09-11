# THBISON — Codex integration master
Status: SOURCE_ASSEMBLY_WITH_VALIDATED_PREVIEW. Not VPS/production-ready yet.
Một gói source Vendor 1–6 theo monorepo, module riêng để tránh đè namespace/migrations. Vendor1 1.0.0-r3 chọn theo nội dung, không theo nhãn lời nhắn. Xem provenance/INPUTS.json.

Đã nối thử source V1→V2 in-process bằng integration/v1-v2-preview.mjs. SEO mock, Knowledge fixture, Writer synthetic, không publish. Chưa nối UI/DB/service processes thành một app hoàn chỉnh. Codex tiếp tục công việc nội bộ theo PROMPT_CODEX.md; không gửi lại vendor theo vòng lặp.

Đọc: AUDIT.md → PROMPT_CODEX.md → docs/INTEGRATION_PLAN.md → docs/VPS_B_RUNBOOK.md.
Kiểm tra gói: `python3 scripts/verify_integrity.py`.
Chạy core checks: `python3 scripts/check_core.py` (Node hỗ trợ strip-types, Python pytest/jsonschema). Không cần npm install để chạy luồng preview nguồn đã chọn.
Chạy riêng: `node --experimental-strip-types --import ./modules/vendor2/tests/register-ts-ext.mjs integration/v1-v2-preview.mjs`.

Không chạy compose như production. deploy/compose.mock.yml là cấu hình lab cần qua build gate. Knowledge và CMS thật giữ tắt. Chưa có SSH/VPS discovery hoặc deployment trong lượt đóng gói này.
