# Kết quả kiểm tra & giới hạn

## Source và độ ổn định đã chứng minh
- V1: 17 core planning tests pass; V2: 29 core tests pass sau sửa đường dẫn test. Không phải full UI suite.
- Reference contract V1/V2: trước 50 pass/1 fail timezone mỗi bộ; sau internal validator patch 51/51 mỗi bộ, giữ nguyên schema và assertions.
- Direct V1 handler→V2 writer: PASS, brief ID/revision liên kết đúng; evidence là fixture, data_class TEST_ONLY. Có payload để kiểm tra lại bằng schema.
- Final source.zip V3/V4/V5/V6 byte-identical bản đã review. Bằng chứng kế thừa: V3 80 pass/1 skip, V4 55 pass, V5 46 pass + clean offline Python3.12, V6 71 pass/2 skip. Không gộp các số đó thành E2E PASS.
- Cùng ContentBrief schema hash ở cả 6 module. Các schema shared được kiểm tra tiếp bằng scripts/check_core.py.

## Patch nội bộ trong gói
1. V2 test fixtures: /workspace/... → process.cwd()/... để chạy từ module cwd; không thay assertion.
2. V1 vendor_kit/tools/contracts.py và V2 vendor-kit/tools/contracts.py: check proposed_publish_at phải có timezone; không chỉnh shared schema, runtime logic hiện đã có check riêng.
3. Thêm integration preview + scripts/provenance/docs/compose lab. Không sửa code V3–V6. Không ghép frontend V1 vào V2 bằng copy đè.
Đã bỏ khỏi source runnable các cache/attachments, bản release lồng, Grok environment metadata/instructions và test runtime data khi phù hợp; giữ license/NOTICE, migrations và fixtures. Input ZIP hashes ở provenance; vendor receipt cũ chỉ là provenance, không dùng làm hash của tree đã chuẩn hóa.

## BLOCKERS Codex phải giải quyết trước VPS stage
B01 npm ci --ignore-scripts --offline trên Node24.19/npm11.9 báo EUSAGE lock thiếu ajv@6.15.0/json-schema-traverse@0.4.1 ở V1/V2. Vendor Docker dùng Node22: xác minh toolchain Node22/npm tương ứng trước kết luận lock corrupt. Không đổi version dependencies hàng loạt. Thử repair package-lock-only offline thiếu cache oxide-wasm; chưa build UI/typecheck/http/ui tests. Lock baseline được giữ lại.
B02 V1 và V2 là hai ứng dụng UI độc lập; luồng DB của V2 vẫn có synthetic planning và local QueuePort. Cần adapter tại ingress/queue/CMS, không dùng kết quả preview in-process như UI E2E.
B03 Persistence V2 fallback PGLite; phải dùng DB staging mới, test create→restart→read. Không gắn DB website VPS A. Build scripts có db:migrate: chỉ chạy với DB test rõ ràng, không inherited production DATABASE_URL.
B04 V3 service/status projection owner decision OPEN; V6 actual adapters cần route mapping chính xác. Không tự đổi schema đóng.
B05 Knowledge V16 chưa kết nối; V4 mock và V6 preflight còn thiếu. Internal backlog giữ missing row parent, per-property data_source mapping, targets ở các trang tiếp, schema identity. Không chạy live Notion để “lấp” mock gap.
B06 Native CMS và actual V3 retry integration chưa được chứng minh. Giữ DRY_RUN/mock, không public publish. Missing endpoints chỉ chặn live, không chặn internal adapter implementation.
B07 Chưa Docker build/compose up, chưa actual six-process E2E, chưa VPS resource/port/service inventory, chưa auth UX/reverse proxy kiểm tra. Không có production readiness claim.
