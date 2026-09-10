# Điều kiện staging — đọc trước khi test

Hub và 4 DB IDs nằm trong STAGING_ACCESS_MANIFEST.json. Link không tự cấp quyền; chưa xác minh account/integration Grok có quyền truy cập.

Cảnh báo nội bộ: bản sao staging có đủ số hàng ở lần kiểm tra trước nhưng remap relation chưa hoàn tất. Lần đo cuối ghi 85 Knowledge Items và 68 Canonical còn relation tới Evidence nguồn; không coi số này là trạng thái hiện tại. Schema trỏ staging không chứng minh page relation đã remap. Không được claim staging isolated hoặc sửa schema/relations hàng loạt để che mismatch.

1. Offline tests trước; ghi source commit, contract digest, version runtime/dependencies.
2. Dùng credential được chủ hệ thống cấp riêng. Thiếu quyền/401/403: dừng nhánh staging, báo BLOCKED_ACCESS, không tìm token khác hay publish DB.
3. Fetch schema, query các trang liên quan, xác minh parent data source của từng relation target. Source production chỉ đọc; tuyệt đối không ghi thông qua relation.
4. Nếu relation trỏ nguồn hoặc sai parent: báo owner, đánh dấu affected test BLOCKED_STAGING_RELATIONS; có thể tiếp tục test trên các hàng synthetic mới tách riêng và chỉ liên kết staging nếu đã được phép.
5. Snapshot trước test; tạo namespace/test_run_id riêng Vendor 3; không sửa Status/Decision/Reviewer Note của bản ghi nền.
6. Write allowlist là bốn DS staging trong manifest, kiểm tra parent của page trước mỗi update. Vendor 3 dùng SQLite/local durable ledger riêng, không ghi ledger vào knowledge DB.
7. Ghi mutation receipt có page ID, parent ID, fields, hash trước/sau, thời điểm và test_run_id, không ghi token.
8. Cleanup chỉ các page/test mutations của run; rollback đúng giá trị trước; báo delta còn lại. Không tuyên bố production delta=0 nếu chỉ có cam kết: cung cấp audit allowlist, log đích ghi và phương pháp đối chiếu.

Expected row counts trong manifest là baseline lịch sử, không phải invariant vĩnh viễn; lệch số hàng phải báo và pin snapshot hiện tại, không xoá dữ liệu để ép khớp.

