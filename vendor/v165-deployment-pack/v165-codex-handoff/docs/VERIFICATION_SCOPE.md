# Phạm vi kiểm chứng gói bàn giao — 2026-09-05

Đây là kiểm tra snapshot và tài liệu bàn giao, chưa phải V16.5 execution.

## Đã kiểm tra trực tiếp từ file người dùng gửi

- ZIP SHA256: `30054428e104f084efd2cd9dea04037c2698cf6cadee99c89e3fb911338823aa`.
- `artifact_hashes.json` SHA256:
  `d154b411445d239a3a4167cf0b52e0158dffe6f49946baa40fe476cd38148aaf`.
- 15 regular files: manifest và 14 members được hash; không thiếu/thừa/duplicate.
- 70 mapping rows, 70 entity IDs và 70 page IDs riêng biệt; 79 issue IDs riêng
  biệt: 70 object issues, 9 condition issues; trạng thái 68 NEEDS_REVIEW, 11 HOLD.
- Hai proposal hashes, semantic hashes và after-value hashes được tính lại.
- Hai pilot targets được trích trực tiếp, liên kết với mapping/base version và
  toàn issue set của entity; cả hai condition UNRESOLVED, exception FALSE kế thừa.
- Review results, accepted derivations và adapter inputs rỗng; canary rỗng,
  authorization false trong snapshot.

`scripts/verify_handoff.py` lặp lại các kiểm tra này và kiểm template activation
chưa duyệt. Các hash là kiểm integrity của checkpoint đã nhận, không tự chứng
minh checkpoint đúng với nguồn pháp lý hoặc live application.

## Chưa kiểm chứng trong gói này

- 242/242 tests, 60/60 V16.4 tests, raw-source re-extraction và replay equality
  là kết quả người dùng báo cáo; chưa chạy lại vì ZIP không chứa repo/source/replay.
- Không có source PDF, trusted reviewer registry, V16.1 canonical file thật hay
  toàn V16.2/V16.3 inputs trong gói. Các manifests chỉ tham chiếu chúng.
- Không đọc live Notion/Kaggle; chưa xác nhận hiệu lực pháp lý, thuật ngữ, ngoại
  lệ hoặc khả năng áp dụng các interval vào thiết bị cụ thể.
- 36 cases trong acceptance matrix là yêu cầu cho Codex triển khai, chưa PASS.
- Không có code V16.5 production hay authorization mới trong gói này.

Sau khi nhận repo, Codex phải ghi kết quả thực đo vào report mới; không sao chép
những tuyên bố đầu vào thành kết quả kiểm thử của mình.
