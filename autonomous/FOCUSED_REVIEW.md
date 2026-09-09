# Focused review — 2026-09-08

Phạm vi đã đọc: machine_admission transport/storage/policy/pipeline/legacy_binding/evaluation; acquisition bridge V16.6; tests mới và test V16.6 bị đổi giới hạn. Không audit lại WooCommerce, VPS, các workflow Notion khác hoặc toàn bộ dependency supply chain. Review do cùng agent thực hiện; không giả reviewer độc lập.

| Vùng | Phát hiện / xử lý | Bằng chứng |
|---|---|---|
| Transport | DNS trước đó không pin connection. Dùng numeric socket + peer address, SSL verification và SNI hostname, từng redirect revalidate trước connect; không dùng proxy env | Rebinding/TLS/private/redirect tests |
| Budget | Chỉ hằng số không giới hạn workload. Reserve byte/hop/model-token trước hoạt động, terminal/deferred URL và attempt count persisted | Stream oversize/global byte/token/restart tests |
| Deadline | Watchdog abort socket, DNS queue timeout, monotonic end-to-end; hai DNS threads tối đa | Timer and slow DNS/stream tests; no live internal probes |
| Integrity | Byte/text/spans/context độc lập; strict typed text và bounded AST, finite numeric predicate | Corruption/extra-key/bool/NaN tests |
| Lineage | Projected record plan không chứa semantic_payload. Sửa JOIN đúng base_version với claim_versions, nối cả alias_key/alias_value, chặn cả unresolved blockers lẫn HOLD | Real 70-row lineage join + mutation tests |
| Eligibility | Không để risk/approval từ source quyết định; chỉ 2 predicates mô tả R1. Unknown/R2 chưa calibrate/R3/UNKNOWN exception giữ lại. Conflicting housing descriptions không thắng bằng vote | Mixed-batch, wrong scope/unit, conflict tests |
| Storage | OS file lock bảo vệ task; commit marker chỉ sau flush result; replay sửa lại DONE nếu crash sau marker; actual os._exit và 2 process contention | Subprocess tests; real pilot/replay |
| Consumer | Recompute từ raw, check current code/policy/config/lineage; scope/use filter; source hashes pinned để revoke cả index và draft local | Rehashed forgery rejected; scoped revoke tests |
| R3 proposals | Full source/text chain và ordinal/printed riêng; không suy luận pháp lý. Hai incomplete proposal giữ unresolved, issue IDs/linkage đầy đủ | Real PDF binding and rehash tamper tests |

Giới hạn không được coi là PASS mở rộng: parser chưa ở worker OS sandbox; watchdog đã được thử với socket giả và tải HTTPS thật nhưng chưa load-test slowloris/IPv6 end-to-end. Semantic lineage chỉ exact aliases/predicate và conservative subject overlap, không phải bộ tương đương ngữ nghĩa đa ngôn ngữ. Không có trained/LLM model, scan OCR benchmark hoặc autonomous gap crawler. Một static preview đã sao chép ra ngoài không thể tự thu hồi. Production adapter/scheduler chưa bật và chưa có căn cứ để bật.

Gate con của scope hẹp đã thực thi; số 401 tests không thay cho benchmark chất lượng trên nhiều nguồn độc lập.
