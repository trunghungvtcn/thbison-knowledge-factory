# JOB_ID=THBISON-INDEPENDENT-AUDIT-01
Đầu vào: MASTER_RELEASE_URL do Codex trả; không dùng release latest khác hoặc r2 guidance làm source candidate.
Đọc release body, SOURCE_MANIFEST.json, SOURCE_SHA, AUDIT_REQUEST.json và hash assets. Clone/download sạch đúng SHA; tự tính hash. Không tin PASS trong report Codex là bằng chứng độc lập.
Thực hiện G0–G10 trong ACCEPTANCE.md trên checkout riêng, không sửa candidate để làm xanh. Provision dependency trước; test offline/local service network chỉ giữa lab processes. Không dùng production env/token.
Tái chạy tests, build và actual process E2E theo lệnh được bàn giao. Tái hiện crash/retry/receipt tamper/real-input HOLD. Đếm JUnit IDs, skipped/NOT_RUN, bind SHA thực tế. Lỗi script hoặc thiếu source là blocker, không bỏ qua.
Notion: chỉ config sandbox chủ dự án cấp riêng; đọc NOTION_READONLY.md. Không target→NOTION_TARGET_MISSING, tiếp tục offline audit. Không xuất private snapshot lên GitHub. Ngrok nếu dùng chỉ là relay tới runner được cấu hình; không tự cấp quyền Notion/GitHub hoặc bật public tunnel.
Trả INDEPENDENT_AUDIT.md + RECEIPT.json + JUnit/log sanitized. Mỗi lỗi ghi gate, severity, file, command/repro, expected/actual; không đề xuất feature mới. Đăng summary lên audit issue Codex tạo, kèm URL artifact và hashes. Không commit sửa source, merge, deploy, scheduler hoặc Notion write.
Verdict: AUDIT_SIMULATION_PASS / AUDIT_FAIL / AUDIT_BLOCKED; real_data_pass riêng. Không gọi synthetic là production-ready. Codex nhận report ở cùng issue; một vòng xử lý lỗi bounded.
