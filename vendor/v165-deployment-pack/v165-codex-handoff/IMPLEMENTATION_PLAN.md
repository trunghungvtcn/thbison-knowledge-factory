# Kế hoạch triển khai V16.5

## Kết quả cần có

Một đường xử lý local chứng minh được: complete record proposal -> semantic review
trên đúng target version -> extension validator -> projected issue ledger và
readiness. Hoàn thành phần kỹ thuật kể cả khi chưa có người duyệt dữ liệu thật.
Không đặt KPI bắt buộc có một record RESOLVED khi evidence/review chưa đủ.

## Baseline và phạm vi

- V16.4 user report: 242 repo tests; 70 records; 79 issues; 0 accepted/resolved.
- V16.1 baseline được báo cáo:
  `af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399`.
- Artifact manifest V16.4 đã kiểm trong ZIP:
  `d154b411445d239a3a4167cf0b52e0158dffe6f49946baa40fe476cd38148aaf`.
- Primary pilot: `0496c4f5-fe89-5d30-b948-34505fb64143`.
- Context/regression: `59957ace-b4fb-519e-b92d-773bc74ad268`.
- Cả hai có object issue và condition issue; `exception_ast` hiện là FALSE.
- Ba prohibition candidate tiếp tục giữ blocker vocabulary. Không đưa vào pilot này.

Các số là checkpoint để đối chiếu, không hard-code vào kết quả ứng dụng. Baseline
repo/source/live phải do Codex ở repo thật tái xác minh.

## Trình tự và phân công theo vai trò

| WP | Công việc | Vai trò | Phụ thuộc | Deliverable / gate |
|---|---|---|---|---|
| A | Freeze và reproduce V16.4 | Codex / kỹ sư repo | Repo thật | Baseline hash, full suite, upstream gates |
| B | Rà soát đầy đủ nguồn cho hai record | Codex chuẩn bị; reviewer đánh giá nghĩa | A | Coverage map và evidence gaps |
| C | Implement extension contract độc lập | Codex / kỹ sư repo | A; contract trong gói | Validator, shadow dispatcher, synthetic tests |
| D | Dựng complete proposal cho primary | Codex | B, C | Một payload/version chứa mọi phần cần sửa |
| E | Review contract và adjudicate record | Người được cấp quyền tương ứng | C, D | Hai loại receipt độc lập, hoặc WAITING |
| F | Project ledger + eligibility | Codex | C; E nếu dùng data thật | Atomic resolution, lineage, blocker accounting |
| G | Full tests và final/replay | Codex | A–F trong phạm vi có thể chạy | Kết quả đo thật và package artifacts |

Không mặc định các vai trò trên là nhiều agent. Codex không được giả reviewer
độc lập. B và C có thể tiến hành không cần chờ có adjudication thật.

## WP A — Snapshot đúng nguồn

1. Đọc AGENTS.md và git status/diff. Không chép code tham chiếu cũ lên code mới.
2. Chạy full repo suite và các gate V16.2/V16.3/V16.4 đang có, giữ nguyên source.
3. Xác minh final-003/replay-003, input/code manifest, baseline thật và raw source.
4. Tải lại review properties bằng đường read-only đã được cấp quyền; lưu timestamp
   và hash snapshot. Không đoán trạng thái nếu snapshot thiếu.
5. Lập inventory keyed bởi issue_id và entity/base_version/issue_type. Xác nhận
   primary có cả hai issue đã trích trong `reference/targets.json`.

Gate A: lỗi checksum/gate nền hoặc state không giải thích được -> dừng xử lý dữ
liệu thật. Vẫn có thể hoàn thiện specification/tests riêng mà không báo repo PASS.

## WP B — Evidence đầy đủ cho record

Không chỉ đọc hai quantity spans. Phải mở toàn bộ mục nguồn, các đoạn trước/sau,
định nghĩa scope, exclusions và cross-reference liên quan; render trang PDF để
so với text extractor. Tự tìm raw bytes trong repo và nguồn đã pin trước khi yêu
cầu người dùng cung cấp lại. Thiếu nguồn thì ghi chính xác source_ref/hash/path.

Source coverage phải có status riêng cho:

| Thành phần | Bằng chứng phải kiểm |
|---|---|
| Quantity và operator | Số, đơn vị và quan hệ ngữ nghĩa, không suy từ số đơn lẻ |
| Condition AST | Cả atomic predicates và từng connective/grouping |
| Exception AST | Những câu giới hạn, ghi chú, điều kiện rút ngắn hoặc dẫn chiếu |
| Applicability | Loại thiết bị, ngưỡng áp dụng, manufacturer/model nếu có |
| Jurisdiction | Phạm vi địa lý của nguồn |
| Legal status | Căn cứ của giá trị đang lưu; không tự coi inherited flag là verified |
| Rule overlap | Record 1 năm/3 năm có cùng thỏa một tình huống không; ưu tiên có evidence không |

Phạm vi review điều kiện không được dùng default FALSE/TRUE để đóng thiếu thông
tin. `exception_assessment` phải phân biệt UNKNOWN, EVIDENCE_BACKED và
NO_APPLICABLE_EXCEPTION_IN_REVIEWED_SCOPE. Trường hợp cuối cần mô tả rõ corpus,
section và reviewer rationale; không suy ra không có ngoại lệ trên toàn thế giới.

Nếu ghi chú chỉ nằm ngoài quote, thêm support spans/context thay vì sửa raw quote.
Nếu lệch do newline/normalization, giữ raw text + map offset qua normalized text;
không đổi nghĩa chỉ để làm exact-match pass.

Artifact locator hiện có `pdf:page:67`; contract-gap ghi `pdf_zero_based_index=66`
và `printed_page_label=68`. Phải tái kiểm mapper của repo và raw PDF. Lưu ba trường
riêng; không mặc định số 67 trong unit_id là zero-based.

Không tự chọn AND/OR từ dấu chấm phẩy/list tags. Model được phép tạo AST proposal
với support map; source reviewer phải xác nhận trước khi dùng để resolve thật.

## WP C — Extension local mới, legacy gate nguyên vẹn

Thêm namespace đề xuất `kf_pilot.v165_complete_record`. Xem contract chi tiết.
Viết dispatcher versioned với hai entrypoints explicit:

- `legacy_literal/v1`: gọi nguyên validator V16.2, giữ nguyên kết quả cũ.
- `complete_record_derivation/v1`: validator mới cho whole-record evidence bundle.

Không dùng fallback kiểu legacy fail -> thử extension. Caller phải chọn route và
pin contract version/hash. Đường mới được implement/test ở LOCAL SHADOW ngay.
Dùng dữ liệu thật ở bước ACCEPT/APPLY chỉ khi có contract activation receipt
và semantic adjudication hợp lệ; template trong gói không phải receipt đã duyệt.

Kết quả extension được ghi vào projected V16.5 ledger riêng. Không viết RESOLVED
trực tiếp vào V16.2 ledger. Chạy gate legacy trên input gốc nguyên vẹn; chạy gate
tương đương trên projection V16.5, có proof nối issue IDs và before/after versions.
PASS legacy không được dùng làm bằng chứng extension đã validate.

## WP D — Một target version cho toàn record

Builder gom object_value + condition_ast + exception_ast và mọi scope chỉnh sửa
có evidence thành một proposal. Gắn đủ original issue IDs; phần ngoài allowlist
giữ nguyên và kiểm diff. Không ghép hai approval V16.4 cũ để tạo approval mới.

Reviewer nhìn được before/after, source spans đầy đủ, truth table đề xuất, overlap
findings, target payload và exact target version. Version dùng identity algorithm
của repo. Dùng sidecar provenance/coverage hoặc schema có version nếu repo không
lưu được các field mới; không loại field để vừa schema cũ.

Nếu một thành phần chưa rõ, xuất draft có completeness status riêng. Không gọi
draft là record-ready và không đưa draft vào derived-value runtime đã kích hoạt.

## WP E — Hai quyết định độc lập

1. Contract activation: người có vai trò phê duyệt contract chấp nhận đúng spec/hash,
   môi trường LOCAL_SHADOW, predicate và target allowlist cụ thể.
2. Record adjudication: reviewer phù hợp chấp nhận đúng bundle hash, toàn bộ issue IDs,
   entity/base/target version, sources và semantic checklist.

Không kế thừa Decision=APPROVED hoặc receipt từ version khác. Không tạo registry
từ candidate. Hash của file không thay thế chứng thực reviewer/quyền phê duyệt.
Thiếu receipt thật thì dừng ở proposal/review pack; vẫn chạy hết synthetic positive
path và real no-accept replay. Không bắt người dùng duyệt trước khi có bản cụ thể.

## WP F — Atomic projection và các blocker mới

Áp dụng object+condition(+exception khi cần) cùng một operation vào bản sao local.
Tất cả validation đạt mới commit projection. Bất kỳ field/issue nào fail thì
không resolve riêng phần còn lại. Lưu original issue IDs cùng resolution event
tham chiếu một target version; không âm thầm tạo ID mới để biến mất issue cũ.

Nếu phát hiện exception/overlap/legal-status gap chưa có trong 79 issue, tạo issue
mới với lineage rõ và đưa vào readiness. Công thức accounting:

`unresolved_after = original_unresolved - original_resolved + new_unresolved`.

Original ledger vẫn nguyên. Báo riêng original resolved, new blockers và tổng
unresolved. Không buộc số issue giữ 79 khi thực sự phát hiện thêm thiếu sót.

Một resolved issue không đồng nghĩa record eligible. Record còn blocker hoặc
HOLD/REJECTED vẫn bị loại. Sau thay semantic version, publication review binding
phải còn hiệu lực đúng version theo policy hiện hành, không tự ghi human fields.

Đọc mới schema/page/parent/before-image bằng quyền hiện có nếu cần đánh giá readiness.
Trong scope này không sinh executable canary; NO_WRITE plan và reasoned exclusions đủ.

## WP G — Kiểm chứng và bàn giao

- Chạy toàn bộ test repo; báo kết quả thực thi, không cộng số test cũ và mới.
- Trường hợp real no-accept giữ mapping/baseline, ledger gốc và human fields nguyên.
- Một target được sửa không làm đổi unrelated records; nguồn liên quan được đọc
  như dependency nhưng không tự sửa secondary entity.
- Chạy độc lập final/replay với input pin giống nhau và as_of cố định, byte equality.
- Gate independent reload raw source, receipts, ledger và tính lại projection;
  self-consistent hash/report không đủ.

Kết thúc hợp lệ có thể là V165_CODE_PASS_WAITING_INPUTS hoặc V165_COMPLETE_RECORD_PROJECTED
với unresolved/eligible đếm thật. Cả hai đều PHASE_F_NOT_AUTHORIZED. Không hứa chắc
thu được record xuất bản nếu evidence/review chưa đủ.
