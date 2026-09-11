# Bàn giao Codex → VPS B
1. Đính kèm toàn bộ ZIP này vào phiên Codex có repo và quyền VPS B phù hợp.
2. Yêu cầu Codex đọc PROMPT_CODEX.md, AUDIT.md và chạy scripts/verify_integrity.py.
3. Codex hoàn tất clean build, UI/DB/service adapters và actual E2E còn mở trước deploy staging. Không gửi vòng vendor mới.

Đã có source đủ Vendor1–6 và luồng V1→V2 in-process đã chạy. Chưa phải ứng dụng all-in-one đã deploy. Knowledge gắn sau, mọi dữ liệu demo TEST_ONLY; CMS live OFF. Không cần anh gom thêm source 1/2 từ các ZIP tên khó nhớ.

Prompt dán ngắn:
“Tiếp nhận THBISON master source. Đọc PROMPT_CODEX.md và AUDIT.md; xác minh hash, xử lý đúng B01–B07 và hoàn tất tích hợp nội bộ theo plan. Knowledge giữ mock, chưa xuất bản thật. Chỉ deploy staging VPS B sau clean-build/persistence/E2E/auth gates. Giữ phần đã pass, không refactor hay mở vòng sửa vendor. Báo kết quả thực cùng evidence, rollback và blockers.”
