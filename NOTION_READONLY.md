# Notion sandbox — input riêng, không đoán ID
Hiện NOTION_TARGET_MISSING. User chưa cấp page/database URL sandbox cho job này.
Chủ dự án điền config local từ example và cấp integration read-only đúng target. Token trong NOTION_TOKEN của runner, không trong ZIP/GitHub/chat report. Không scan workspace/search rộng hoặc lấy ID từ snapshots lịch sử.
Auditor đọc schema/properties, phân trang rows/blocks thuộc target được chỉ định trong giới hạn config; related databases chỉ đọc nếu có trong allowed_targets. Dừng khi vượt scope. Không sửa page/property, không duplicate staging, không gọi production.
Đối chiếu property type, schema identity, pagination và field mapping EvidenceBundle; trường thiếu/mismatch báo BLOCKED, không sửa schema để khớp.
Raw snapshot lưu ngoài repo public trong storage riêng do chủ dự án cấp. Public report chỉ status, counts, schema hash đã lọc và opaque reference; không public URL/ID/private rows nếu chưa cho phép.
Không đánh đồng hash report/JUnit với hash corpus.
