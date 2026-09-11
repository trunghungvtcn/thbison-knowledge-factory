# Public master link
User cho phép publish candidate code đã lọc, không cho phép public dữ liệu riêng.
Ưu tiên public repo Knowledge hiện có với integration branch + prerelease mới thbison-integration-01-rc1. Không đổi tag cũ. Nếu repo đích private, không đổi visibility toàn repo; tạo public candidate repo riêng sau khi xác minh không trùng tên và đủ quyền.
Review toàn bộ tree/archive trước public: .env, token, Notion snapshots/IDs, corpus, customer data, logs, nested ZIP, SQL dumps. Payload Content OS nguyên bản trong gói bàn giao KHÔNG tự động được phép đẩy nguyên lên public; extract và phân loại trước. Giữ license/NOTICE.
Tạo SOURCE_MANIFEST.json (component repo/source SHA/delta/import hashes), SOURCE_SHA, exact commands, env.example, COMPOSE_LAB.md, REPORT_CODEX.md, AUDIT_REQUEST.json, PROMPT_GROK_AUDIT.md, ACCEPTANCE.md.
Release assets: source sanitized zip, audit-kit.zip, evidence-sanitized.zip, SHA256SUMS. Deterministic ZIP cần thứ tự, timestamp, permissions cố định; zip -X một mình không đủ. Tải lại, kiểm tra hash. Không đặt outer zip hash vào chính zip.
Release body là master index: source SHA, các component pins, gates, audit issue, asset links, Notion status và hướng dẫn 1 lệnh up/test/down. Chỉ phát hành sau candidate report hoàn tất; failure cũng được phát hành nếu ghi rõ BLOCKED, không gọi ready.
Nếu token không có write/release: lưu artifact local và báo BLOCKED_PUBLISH_PERMISSION; không sửa permissions để vượt chặn. Không yêu cầu user copy nhiều job: một Release URL → Grok audit → một issue → Codex.
