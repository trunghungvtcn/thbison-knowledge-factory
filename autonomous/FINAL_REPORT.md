# Knowledge Factory — execution report

Thời điểm báo cáo: 2026-09-08T01:11:29.434374+00:00. Phạm vi: **LOCAL_SHADOW**, không phải deploy production.

| Capability | Kết quả | Bằng chứng |
|---|---|---|
| Code | CODE_READY cho lát cắt local hẹp; 401/401 tests | artifacts/final-tests.log |
| Nguồn → knowledge → preview | MACHINE_LANE_WORKING, dữ liệu OEM thật | artifacts/final-pilot.log |
| Chất lượng đã đo | DATA_QUALITY_MEASURED, 48 ca consistency | MODEL_EVALUATION.json |
| ML/LLM | NOT_RUN / NOT_CALIBRATED | Không gọi provider, không train/calibrate |
| OCR | NOT_RUN | PDF text-layer extraction không tính OCR |
| Production | NOT_DEPLOYED | authorized_to_execute=false; không SQL/scheduler/Phase F |

## Kết quả thực

- Đã tải 3/3 tài liệu công khai, 2,204,188 byte, 3 HTTP hops; mỗi URL 1 attempt. Giữ nguyên raw để replay, không tải lại sau đó.
- 6 candidate: {'MACHINE_ACCEPTED': 4, 'REVIEW_EXCEPTION': 2}. Preview có 4 snippet đúng nguồn. Hai housing descriptions bị giữ do giá trị cạnh tranh; không ép merge. Từ vựng gần nhau vẫn có thể là paraphrase: coverage hữu ích chỉ 2 nhóm scope/predicate, không quảng cáo 4 knowledge độc lập.
- 1 provenance family được tính bảo thủ cho ba trang Harrington/KITO; không tính thành ba authority độc lập.
- Queue 4 mục, gồm 2 R3 legacy và 2 candidate mới. 85 issue legacy vẫn mở. Không ghi Decision/Reviewer Note hoặc giả approval.
- Hash baseline trước/sau: `af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399`. Mapping 70/70; issue IDs nguyên vẹn 79+6=85; human/mapping/baseline file hashes bằng nhau.
- Ba span PDF (ordinal/printed: 67/68, 62/63, 8/6) đã đối chiếu raw/text/offset/full context và ảnh render. Hai proposal có base version, proposal hash, corpus/time, issue set; AST/exception giữ UNRESOLVED, chưa đủ để adjudication.
- Benchmark tự sinh: 4 positive + 44 deliberate mutations; 0 lỗi consistency quan sát. Không phải expert gold. Không có CI/độ chính xác pháp lý/ngữ nghĩa tổng quát; chỉ 1 family và n=4 positive. Không được gọi đây là “ML chính xác 100%”.
- Replay cùng task `03f199dfd9d46ec430c4b3642a0797b4ec0dfa2203c59a7b7d8b9f88fd326b40`, cùng pins/hash, không thêm request/byte hay duplicate commit ở revision code cuối. Initial run khác code revision được giữ trong checkpoint để audit.

## Code và ranh giới

Release code hash: `0d0174eeabfa7a2a55dbdd05774c5b1180114c1f0074441daccefd2d3fff51bf`. Git HEAD `dc018b6136bbc08f859ddd29c8b24b4f35ba8d9d` không phải release commit: subtree Knowledge Factory vốn chưa tracked trong worktree đang có nhiều thay đổi khác.

Thêm machine_admission: transport pinned IP/TLS, budget bền qua restart, strict policy/lineage, commit/index/revocation, consumer verifier, benchmark và legacy span binding. Sửa acquisition V16.6 dùng transport mới và cập nhật giới hạn test 32→20 MiB, 3→2 attempts theo pack. Không sửa WooCommerce/frontend/backend/VPS A. CODE_MANIFEST liệt kê chính xác file; patch chỉ chứa file mới, file cũ sửa được cung cấp nguyên after-image. Hai before-image source không được chụp riêng: không giả đó là rollback backup.

Regression baseline 336 tests; final 401 tests. Hai lỗi test mới (NameError do đặt assertion sai chỗ; khác đường deadline) đã sửa, giữ log correction-01/02. Không sửa ngưỡng acceptance để tăng tỷ lệ nhận claim. Rà soát tập trung ghi ở FOCUSED_REVIEW.md.

## Còn thiếu, điều kiện chạy tiếp

| Phạm vi | Blocker / trigger | Người phụ trách |
|---|---|---|
| ML/LLM evaluator/provider adapter | Chưa tích hợp provider/adapter thực, chưa có nhãn độc lập nhiều families; bổ sung gold theo mẫu và benchmark trước promotion | ML engineer / qualified reviewer |
| OCR | Chưa có benchmark scan; cần scan + ground truth trước khi cho OCR output vào admission | Data engineer |
| Tự tìm nguồn theo gap | Pilot dùng 3 seeds đã chọn; novelty/retry primitives có test nhưng tự tìm URL, 4 URL/round và continuous queue chưa triển khai end-to-end | Data engineer |
| Legal R3 | Đủ source text không thay cho phê duyệt grouping/exception/overlap/legal applicability | Qualified legal/domain reviewer, không mặc định chủ DN |
| Scale/multi-host | Chưa có parser sandbox cấp OS, multi-host coordinator, throughput/drift benchmark | Deployment operator |
| Notion/Kaggle production | Chưa nằm trong scope job; cần release-bound canary + staging before-image/rollback và approval riêng | Deployment operator |

## Riêng tư, verification và rollback

Raw nguồn và `artifacts/legacy-binding/bindings-private.json` cùng 70 snapshots giữ tại repo, loại khỏi ZIP. Delivery là source overlay/attestation cho repo hiện có, không phải verifier standalone trên máy trống. Chạy các lệnh ở README; `read_current` luôn re-open raw, legacy lineage và tái tính, không chỉ kiểm output hash.

Không có production writes/SQL/schema/scheduler/Notion/Kaggle actions được thực hiện trong job. Đây là phạm vi hành động đã thực hiện, không phải một audit toàn bộ activity logs của server bên ngoài. Không có production state cần rollback. Lộ trình staging/canary và điểm backup trước write ghi trong README, chưa thực thi.

Kết luận: **lát cắt direct-extraction local dùng được với nguồn thật; mở rộng tự động/ML chưa được hiệu chỉnh và production chưa triển khai.**
