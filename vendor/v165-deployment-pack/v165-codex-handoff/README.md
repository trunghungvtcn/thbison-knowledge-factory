# V16.5 — Complete Record Remediation — gói giao Codex

Đây là **plan và specification để triển khai trong repo thật**, không phải một
V16.5 đã chạy. Gói kèm snapshot V16.4 thật do người dùng cung cấp để kiểm tra đầu vào.

## Giao việc

1. Đính kèm ZIP này vào phiên Codex đang giữ repo Knowledge Factory.
2. Dán nội dung `PROMPT_CODEX_V165.md` vào phiên đó.
3. Codex phải viết và test extension ở namespace mới, dựng proposal hoàn chỉnh cho
   một record và báo các blocker cụ thể. Chỉ chạy LOCAL / NO_WRITE.

## Khác biệt của bước này

V16.4 có 2 quantity proposals nhưng **cả hai record đều còn condition UNRESOLVED**.
Duyệt quantity riêng rồi sửa condition sau sẽ đổi target version và làm approval
cũ không còn áp dụng. V16.5 ghép object value, condition, exception, applicability
và source coverage thành **một target version**, duyệt một bundle có hash.

Triển khai extension `complete_record_derivation/v1` ở đường local shadow riêng.
Đường V16.2 whole-literal và artifacts cũ giữ nguyên. Không yêu cầu extension mới
phải giả dạng literal cũ để được đi tiếp; cũng không đổi luật của legacy validator.

Pilot đề xuất: entity `0496c4f5-fe89-5d30-b948-34505fb64143` (proposal quantity 3 năm
trong snapshot). Lý do chọn: record này có 2 legacy condition tags, ít nhánh hơn
record 1 năm có 4 tags. Đây là lựa chọn công việc, không xác nhận quy định áp dụng.
Record 1 năm được đối chiếu ngữ cảnh/overlap và giữ làm regression case.

## Nội dung

| File | Mục đích |
|---|---|
| `PROMPT_CODEX_V165.md` | Prompt hành động để giao Codex |
| `IMPLEMENTATION_PLAN.md` | Work packages, dependencies, outputs và stop rules |
| `contracts/COMPLETE_RECORD_V1.md` | Đặc tả extension và atomic multi-issue resolution |
| `contracts/contract_activation.template.json` | Mẫu DRAFT, chưa cho phép dùng dữ liệu thật |
| `docs/ACCEPTANCE_MATRIX.md` | Test bắt buộc và ý nghĩa từng PASS |
| `docs/EXPECTED_REPORT.md` | Mẫu báo cáo, không có số PASS được điền sẵn |
| `docs/VERIFICATION_SCOPE.md` | Phần đã kiểm chứng ở bước đóng gói |
| `reference/final-003.zip` | Bytes nguyên gốc người dùng cung cấp |
| `reference/targets.json` | IDs/hash/blocker trích từ artifact thật |
| `scripts/verify_handoff.py` | Kiểm integrity và liên kết target trong gói |

```bash
python scripts/verify_handoff.py
```

Lệnh này kiểm package đầu vào, **không chạy 242 test của repo**, không re-extract
PDF gốc, không kiểm live Notion và không xác nhận chính sách kỹ thuật/pháp lý.

Không có adjudication ACCEPT, reviewer registry mới hay production authorization
được tạo trong gói. Thiếu các đầu vào này vẫn phải hoàn tất code, tests synthetic,
evidence audit và proposal/review pack có thể làm được trước khi báo blocker.
