# Knowledge Factory: local shadow deployment candidate

Đã tích hợp vào repo Knowledge Factory hiện có. Đây không phải một bộ cài VPS hoặc một phiên bản đã triển khai Notion/Kaggle production.

## Chạy lại có kiểm chứng

Thư mục làm việc: `kaggle-pilot-jupyter`. Dùng Python 3.12 và bộ dependencies V16.6 sẵn có; Python 3.14 hệ thống không tương thích các wheels này.

```powershell
$env:PYTHONPATH="$(Get-Location)\src;$(Get-Location)\v166\completion\deps"
$kfPython='C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $kfPython -m pytest -q
& $kfPython -m kf_pilot.machine_admission.pipeline --config autonomous/run_config.json --output autonomous/artifacts/pilot-001
& $kfPython -m kf_pilot.machine_admission.evaluation --config autonomous/run_config.json --root autonomous/artifacts/pilot-001 --output autonomous/MODEL_EVALUATION.json
& $kfPython -m kf_pilot.machine_admission.legacy_binding --output autonomous/artifacts/legacy-binding
```

Không thêm `--online` để replay. Dữ liệu OEM đã đóng băng ở `artifacts/pilot-001/raw`; các bộ đếm nằm trong checkpoint của cùng thư mục. Không xóa checkpoint hoặc đổi thư mục để né giới hạn tải/retry. Không chạy song song hai lệnh cùng output: worker thứ hai sẽ dừng BUSY, không chờ quay vòng.

`read_current(config_path, root)` là cửa đọc có kiểm chứng dành cho consumer: kiểm source, code, policy, lineage và tái dựng từ raw. Không dùng `result.json` đọc trực tiếp làm API sản xuất. `invalidate(root, dependency_hash)` thu hồi chỉ bản nháp local phụ thuộc; bản đã xuất ra ngoài không thể tự thu hồi, vì vậy chưa publication.

## Phạm vi hiện dùng được

Nguồn OEM HTTPS công khai → raw/hash → trích text HTML → nhận định theo danh mục predicate cố định → kiểm chứng span/context/model → MACHINE_ACCEPTED hoặc queue → index và preview local. Dùng rule xác định, không dùng một mô hình ML đã huấn luyện. Hai nhóm nội dung hẹp là vật liệu vỏ và thành phần truyền động, chỉ cho `DESCRIPTIVE_DRAFT` đúng hãng/model. R2 chưa hiệu chỉnh và R3/pháp lý không tự nhận.

Planner hiện là 3 seed OEM đã chọn theo subtopic, không phải crawler tìm mọi website hoặc agent tự nghiên cứu vô hạn. Primitive novelty/retry/checkpoint đã kiểm thử; tìm thêm URL tự động theo gap, bounded parser worker cấp OS, LLM provider adapter và vận hành nhiều máy chưa hoàn tất. Không bật scheduler.

## Riêng tư và khôi phục

Delivery ZIP là overlay **chỉ cho repo Knowledge Factory hiện có**. Có source thay đổi, test, report, metrics và log; không kèm raw corpus, 70 Notion snapshots, reviewer notes, credentials hay toàn bộ repo WooCommerce. Vì thế ZIP không đủ tự chạy verifier legacy trên máy trống; dùng raw/inputs đang có trong repo này.

Không có production mutation để rollback. Hai file hiện hữu đã sửa là acquisition V16.6 và test giới hạn; các file machine_admission/autonomous là mới. Bản mã trước khi sửa hai file này không được chụp riêng trong job; không coi manifest cũ là backup byte-for-byte. Muốn quay lại local, trước tiên lưu artifact/source hiện tại và dùng revision/backup V16.6 được xác minh, không reset worktree chung.

## Đường triển khai production chưa thực thi

1. Chốt exact source manifest/hash từ báo cáo này. Không lấy toàn workspace dirty làm release.
2. Đóng gói runtime riêng, không chạm frontend/backend VPS A; network egress public-only, parser hạn tài nguyên cấp OS.
3. Canary tối đa 3 record R1 mới trong staging riêng, snapshot schema/pages/human fields, before-image + rollback đã flush trước mutation.
4. Ánh xạ Evidence Sources / Knowledge Items có contract và idempotency; kiểm read-back, replay zero semantic delta, rollback và độc lập verify.
5. Chỉ sau phê duyệt riêng mới ghi Notion/Kaggle production. SQL, scheduler, schema mutation, Phase F đều chưa được job này bật.
6. Chỉ tăng quy mô khi có benchmark nhiều provenance families, precision/coverage phù hợp từng predicate, ngân sách chi phí và đo throughput. OCR/ML phải có benchmark riêng trước khi đưa vào admission.
