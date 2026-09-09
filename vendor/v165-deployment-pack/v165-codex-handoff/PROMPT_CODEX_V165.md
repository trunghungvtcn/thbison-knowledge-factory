# Giao Codex: triển khai V16.5 Complete Record Remediation

Hãy thực hiện code và kiểm thử trong repo Knowledge Factory thật, sử dụng gói
bàn giao này. Không chỉ trả về một plan mới. Phạm vi được giao là **LOCAL /
NO_WRITE**, namespace mới `kf_pilot.v165_complete_record`. Không triển khai
production, push Kaggle, ghi Notion, chạy SQL, đổi schema, bật scheduler/farming.

Đọc `README.md`, `IMPLEMENTATION_PLAN.md`, `contracts/COMPLETE_RECORD_V1.md`,
`docs/ACCEPTANCE_MATRIX.md` và `docs/EXPECTED_REPORT.md` trước khi sửa code.
Tuân thủ AGENTS.md trong repo. Không ghi đè thay đổi người dùng hay artifacts cũ.

## Mục tiêu thực chất

V16.4 tạo được hai quantity proposals nhưng cả hai còn condition UNRESOLVED.
Chưa có adjudication, accepted derivation hay canary. V16.2 không chấp nhận
prose-to-scalar vì contract whole-literal. Chạy lại cùng đường cũ sẽ không giải
quyết được nút thắt này.

Xây extension contract riêng `complete_record_derivation/v1`, có validator và
local shadow projector riêng, để đưa **toàn bộ semantics của một record** vào
một proposal, một target version, một lần review. Giữ nguyên đường
`legacy_literal/v1` và gates V16.2; extension không được tự động fallback hoặc
giả danh một V16.2-compatible input.

Pilot chính: `0496c4f5-fe89-5d30-b948-34505fb64143`, quantity proposal 3 năm.
Đối chiếu record `59957ace-b4fb-519e-b92d-773bc74ad268`, proposal 1 năm, để kiểm
ngữ cảnh và overlap. IDs/hash/issue IDs chính xác ở `reference/targets.json`.
Chọn pilot này vì ít legacy tags hơn, không phải vì đã xác nhận quy định đúng.
Không hardcode 3 năm thành khuyến nghị an toàn hoặc quy định áp dụng mọi hãng.

## Thứ tự thực hiện

1. Chạy `python scripts/verify_handoff.py` từ thư mục gói bàn giao. Kiểm kê repo,
   raw sources, V16.1–V16.4 artifacts, commands và dependencies thật. Hash baseline
   được báo cáo là `af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399`.
   Tự kiểm tra file baseline thật. Con số 242 tests là báo cáo đầu vào, cần chạy
   lại suite hiện có và ghi kết quả thực tế. Không tạo fixture thay cho repo
   thật rồi gọi đó là repository acceptance. Nếu thiếu repo, ghi chính xác input
   thiếu; phần độc lập còn làm được phải hoàn tất và ghi rõ chưa tích hợp.
2. Reproduce gates cũ trên artifacts cũ vào output mới. Nếu baseline mismatch,
   giữ bằng chứng và không chiếu kết quả vào baseline sai. Không sửa expected
   hash/test để biến lỗi thành PASS.
3. Audit raw source của hai interval: hash, extractor, locator, exact spans,
   toàn mục liên quan, định nghĩa, phạm vi, ngoại lệ và các dẫn chiếu. Snapshot
   ghi locator `pdf:page:67`, zero-based index 66, printed page 68; phải xác minh
   mapping này từ source/extractor thật. Nếu version extractor không có, giữ
   lineage của extraction mới; không gắn offsets cũ vào text mới.
4. Xây `field_support_map` cho object, condition, exception, applicability,
   jurisdiction, legal-status/time scope. UNRESOLVED phải còn là chưa giải
   quyết khi thiếu bằng chứng. `exception_ast: FALSE` được kế thừa không chứng
   minh không có ngoại lệ. Không suy AND/OR từ tags hoặc từ mục tiêu tăng resolved.
   Kiểm tra khả năng một thiết bị thỏa cả hai interval; phải có evidence và
   review cho precedence/exception, hoặc ghi blocker rõ ràng. Không kế thừa
   `CURRENT_REFERENCED_BY_19_2025_TT_BNV` như một sự thật đã được kiểm chứng.
5. Implement strict schemas, deterministic canonicalization/hash, contract
   dispatcher, complete-record validator, review validation, projector và
   independent gate. Dùng identity contract thật của repo, không tự đổi hàm
   entity/version ID. Proposal phải bao gồm diff, toàn semantics, all issue IDs,
   source/coverage/dependency hashes, base version và target version cuối cùng.
   Chưa đủ evidence vẫn xuất draft + review work, nhưng không mark complete.
6. Tạo contract spec versioned để reviewer kiểm tra. Template activation trong
   gói là NOT_APPROVED; nó không cấp quyền APPLY real data. Thiếu activation
   độc lập không cản viết code, synthetic tests, audit hay đề xuất contract.
   Không tự tạo reviewer đáng tin, tự ACCEPT hoặc dùng AI critique làm human
   adjudication. Dữ liệu fixture phải TEST_ONLY và bị chặn khỏi đường real data.
7. Xây review pack cho trọn record. Một ACCEPT hợp lệ phải bind đúng contract,
   proposal hash, full semantic payload, issue set, entity/base/target version,
   source dependencies và registry/reviewer scope/time. Review riêng quantity
   cũ không được chuyển sang bản có condition mới. Decision/Reviewer Note trên
   Notion chỉ là audit input; không tự chuyển nghĩa hoặc ghi đè.
8. Test atomic projection bằng synthetic accepted case: object và condition
   được giải quyết cùng target version hoặc rollback cả hai. Ledger V16.2 gốc
   giữ nguyên; projected ledger V16.5 phải giữ lineage tất cả 79 issue IDs.
   Blocker mới về ngoại lệ/overlap/legal validity phải được ghi thêm, không bỏ
   qua để giữ số 79 đẹp. Existing HOLD tiếp tục chặn nếu chưa có căn cứ release.
9. Chạy các case trong acceptance matrix, full repo suite và independent gate.
   Gate phải tự đọc source/manifests/review inputs rồi recompute, không chỉ tin
   readiness_report hoặc hashes do producer tự ghi. Chạy final và replay riêng;
   canonical outputs phải deterministic, runtime metrics đặt ngoài nội dung
   cần byte equality. Kiểm tra mutations bằng transport guard/spies, không chỉ
   bằng config NO_WRITE. Không thêm production transport vào namespace này.
10. Với data thật, nếu thiếu evidence/activation/adjudication, hoàn tất proposal,
    review pack, blocker list và báo `V165_CODE_PASS_WAITING_INPUTS` khi code
    gates thực sự PASS. APPLY real data là NOT_EXECUTED, không phải fake pass.
    Nếu đã có đủ input độc lập hợp lệ, chỉ chiếu LOCAL_SHADOW và kiểm gates mới;
    trạng thái tối đa `V165_COMPLETE_RECORD_PROJECTED / PHASE_F_NOT_AUTHORIZED`.
    Canary vẫn records=[] và authorized_to_execute=false trong job này.

## Yêu cầu bàn giao cuối

- Source mới, integration diff nhỏ, tests, runnable CLI và commands chính xác.
- Logs suite/gates; liệt kê PASS/FAIL/NOT_EXECUTED theo test và data class.
- Artifacts theo `docs/EXPECTED_REPORT.md`, phân biệt original ledger và shadow.
- Report số issues resolved thực tế, blockers mới, nguyên nhân chưa hoàn chỉnh;
  không đặt KPI bắt buộc phải có một real record RESOLVED khi bằng chứng thiếu.
- So sánh baseline trước/sau, giữ nguyên 70 entity/page mappings và human fields.
- ZIP allowlisted chứa source/tests/docs/artifacts/manifests, không secrets,
  credentials, caches hay dependencies. Tách dữ liệu không được phép chia sẻ.
- Không ghi “production-ready”, “canary-ready” hoặc “toàn pipeline hoàn tất” từ
  việc tests/local projection PASS. Không nới gate chỉ để đạt kết quả mong muốn.

Không dừng xin xác nhận cho các bước local được giao. Hoàn tất tất cả công việc
có thể làm và trình bày bộ proposal/contract cụ thể để người có thẩm quyền duyệt.
Nếu thiếu input độc lập, báo đúng tên file/hash/scope cần bổ sung cùng phần đã
hoàn tất; không bịa input và không lặp lại cùng một pipeline không tạo tiến triển.
