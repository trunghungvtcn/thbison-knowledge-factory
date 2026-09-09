# Báo cáo triển khai V16.5

Trạng thái: `V165_CODE_PASS_WAITING_INPUTS / PHASE_F_NOT_AUTHORIZED`.

Phạm vi đã thực hiện: LOCAL / NO_WRITE. Đã xây extension complete-record, CLI,
validator, kiểm tra activation/adjudication và atomic shadow projector trong repo.
APPLY dữ liệu thật: **NOT_EXECUTED** vì proposal còn thiếu bằng chứng và chưa có
activation/adjudication độc lập. Không có record thật được tuyên bố RESOLVED.

## Kết quả đo

| Hạng mục | Kết quả |
|---|---|
| ZIP handoff | V165_HANDOFF_PACK_VERIFIED |
| Full suite trước thay đổi | 242 PASS, 0 FAIL |
| Full suite sau thay đổi | 295 PASS, 0 FAIL |
| Test V16.5 mới | 53 case được chạy trong full suite |
| Gate V16.2 ledger/readiness | PASS |
| Gate V16.3 source binding | PASS |
| Gate V16.4 independent/replay | PASS |
| Gate V16.5 tái tính từ nguồn | V165_INDEPENDENT_GATE_PASS |
| Final/replay | 19 file byte-equal |
| Synthetic atomic ACCEPT | PASS, TEST_ONLY, cùng validator với repository |
| Synthetic rollback giữa chừng | PASS, không resolve riêng một phần |

Log thực thi nằm trong `v165/logs/`; hướng dẫn chạy tại `v165/README.md`.
Working-tree changes: namespace `src/kf_pilot/v165_complete_record/`,
`tests/test_v165_complete_record.py`, và `v165/`. Không tạo commit trong worktree
đang có thay đổi của người dùng. Implementation V16.1–V16.4 được giữ nguyên.

## Dữ liệu thật và accounting

| Số đo | Giá trị |
|---|---:|
| Entity/page mappings | 70 |
| Mapping thiếu/trùng | 0 / 0 |
| Issue gốc chưa giải quyết | 79 |
| Issue gốc RESOLVED trong projection | 0 |
| Blocker mới | 6 |
| Tổng chưa giải quyết trong ledger V16.5 | 85 |
| Complete-record drafts | 2 |
| Record thật đã project | 0 |
| Thay đổi record ngoài pilot | 0 |
| Adjudication ACCEPT/REJECT/HOLD/NEEDS_MORE_EVIDENCE | 0 / 0 / 0 / 0 |

Sáu blocker mới gồm ba loại cho mỗi pilot: `EXCEPTION_COVERAGE_UNKNOWN`,
`RULE_OVERLAP_UNRESOLVED`, `LEGAL_STATUS_UNVERIFIED`. Mỗi blocker có ID deterministic,
nguồn và lineage về các issue gốc. Công thức kiểm: **79 - 0 + 6 = 85**.
Ledger V16.2 gốc vẫn 0 RESOLVED / 11 HOLD / 68 NEEDS_REVIEW.

Primary: `0496c4f5-fe89-5d30-b948-34505fb64143`.
Base version: `cv_be9140613fe23ef6ca60dde1979a4704c97341ff5f562be88027e1c0dffe3b6c`.
Draft proposal hash: `c93810a4a8b3b8ada1038872063012e6fd1c982b1d1df4d4e948942348a7d1f9`.

Context/regression: `59957ace-b4fb-519e-b92d-773bc74ad268`.
Base version: `cv_dcaf9914d5b47c39abbce4b96cb92145a8352b2c1dc63ed14bbe2def740f99a6`.
Draft proposal hash: `4056fee5983e3cadca0d1054171135d34e0d40b2933c43ee6b975f5bd97f3796`.

Cả hai `target_version_id=null`: draft chưa đủ semantics để tạo accepted runtime
version. Condition UNRESOLVED và exception FALSE cũ còn hiển thị nguyên trạng trong
before/after, nhưng completeness là UNKNOWN; không dùng chúng như bằng chứng.

## Audit bằng chứng

Raw PDF được kiểm hash và tái trích xuất bằng `pymupdf:1.28.2:sort=True`, đối chiếu
với catalog V16.3. Toàn các trang thuộc page scope đã pin được đưa vào source bundle.
Đã render bằng Poppler và xem trực tiếp trang quy định khoảng kiểm định và trang
phạm vi/định nghĩa: ordinal 67 → index 66 → printed label 68.

Quantity: SUPPORTED ở mức trích xuất trực tiếp. Applicability/jurisdiction:
SUPPORTED theo văn bản nguồn, chưa phải chứng nhận hiệu lực hiện hành.
Conditions: UNKNOWN. Exceptions: UNKNOWN. Legal status: UNKNOWN. Overlap: UNRESOLVED.

Mục 10.2–10.4 chứa điều khoản thời hạn ngắn hơn, yêu cầu ghi lý do và dẫn chiếu
quy chuẩn. Vì vậy inherited exception FALSE không chứng minh không có ngoại lệ.
Tình huống thiết bị cố định có mái che nhưng hơn 12 năm được đưa vào review pack
để xem xét khả năng chồng lấn; không tự chọn khoảng nào ưu tiên và không tự suy AND/OR.
Đây là audit dữ liệu nguồn, không phải khuyến nghị khoảng kiểm định cho thiết bị cụ thể.

Các dẫn chiếu QCVN/TCVN và căn cứ cho `CURRENT_REFERENCED_BY_19_2025_TT_BNV` chưa có
corpus cập nhật được xác minh đầy đủ trong lần chạy này. Giới hạn này đã thành blocker.

Đã fetch lại **hai trang pilot và schema** bằng connector Notion read-only, lưu
response, timestamp và hash tại `v165/inputs/pilot_reviews.json`. Hai Decision vẫn
PENDING; reviewer notes giữ nguyên. **68 trang còn lại dùng snapshot V16.3 đã pin**,
không tuyên bố đã refresh toàn bộ 70 trang. Không thực thi SQL khi đọc schema.

## Contract và các input còn thiếu

Contract: `complete_record_derivation/v1`.
SHA256 của spec cung cấp trong handoff:
`7103b106dd6d09c46ac96cc2f97986b201e354afa82f58395e9b59726f126fa8`.
Activation: NOT_SUPPLIED; template NOT_APPROVED không được dùng làm receipt.

Để tiến tới real LOCAL_SHADOW APPLY cần:

1. Bằng chứng và review cho condition grouping, exception/precedence và legal/time
   scope của **toàn record**. Review draft tại `artifacts/final-001/review_pack.md`.
2. `inputs/reviewer_registry.json` từ nguồn thẩm quyền độc lập: role, predicate/entity
   scope, data class và thời hạn hiệu lực. Hash do bên phê duyệt xác nhận độc lập.
3. `inputs/contract_activation.json` phê duyệt đúng spec hash ở trên, môi trường
   LOCAL_SHADOW và allowlist entity/predicate cụ thể.
4. `inputs/complete_record_adjudications.jsonl` bind proposal hoàn chỉnh, toàn issue
   set, source coverage, base/target version cuối cùng. Draft hiện tại chưa đủ điều
   kiện ACCEPT; review quantity V16.4 không được chuyển sang whole-record approval.

Không cần gửi token vào chat. Những input thiếu ở đây là evidence và receipt review.

## Integrity, mutations và giới hạn publication

Canonical baseline trước/sau giống nhau:
`af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399`.

Runner hash inputs trước/sau, kiểm legacy code/manifests và tái chạy V16.2 compute
thật với empty evidence cùng snapshot pilot mới. Gate V16.5 tự reload input, raw
sources, schema/snapshot và dựng lại outputs; test sửa report rồi rehash vẫn bị phát hiện.

Observed network/SQL/process attempts trong offline runner: **0 / 0 / 0**.
Các guard đã được thử bằng call bị cấm và đều chặn thực thi. Human-field,
production, CREATE, SQL, schema và scheduler mutations: **0**.

Production eligibility: **NOT_EVALUATED_NO_COMPLETE_RECORD** (`null`, không phải
production-ready). Publication review: NOT_EVALUATED_NO_TARGET cho real drafts;
synthetic projection đánh dấu cần review lại target version. Canary: records=[];
`authorized_to_execute=false`. Không có Kaggle run hoặc Phase F.

## Artifacts

Final: `v165/artifacts/final-001`; replay: `v165/artifacts/replay-001`.

SHA256 `artifact_hashes.json`:
`18881a81ba156bb120242ca0159391c23586b3099f08a9c5c19ce8b6df655bda`.

SHA256 `complete_record_proposals.jsonl`:
`6684cccfd772a7c6db1993435cf199a4ac9b2969ae7d085f7a47b96d332fea82`.

SHA256 `code_manifest.json`:
`9660a7a8d46f037a9f8eb735b7310478c9cb0ddcbbd1e5770c9762c889835e54`.

Delivery ZIPs được tạo riêng: code/tests/report và audit PRIVATE_LOCAL_ONLY.
Audit chứa page IDs, source quotes và reviewer snapshot; không upload/chia sẻ.
Archive allowlist loại credentials, dependencies và caches; có manifest và ZIP
integrity verification. Hai ảnh audit PDF được lưu riêng trong private bundle.
