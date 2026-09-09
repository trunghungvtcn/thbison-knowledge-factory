# Draft contract — complete_record_derivation/v1

Trạng thái specification: DRAFT_FOR_REPOSITORY_REVIEW. Được dùng để implement và
kiểm thử local shadow; không phải semantic adjudication hoặc quyền production.

## 1. Bản ghi đề xuất

```text
CompleteRecordProposal
  contract_id / contract_version / contract_spec_hash
  identity_contract_id
  data_class: TEST_ONLY | REPOSITORY
  mode: LOCAL_SHADOW
  entity_id / base_version_id / target_version_id
  page_id / parent_id
  original_issue_ids[]
  before_record_hash / after_semantic_hash
  before_semantic_payload / after_semantic_payload
  allowed_changed_fields[] / actual_field_diff[]
  source_bundle[]
  field_support_map{}
  completeness_assessments{}
  source_coverage_hash
  upstream_v164_proposal_hashes[]
  dependency_records[]
  new_blockers[]
  proposal_hash
```

Hash canonical deterministic, bao gồm các thành phần evidence/contract/identity
liên quan. Không đưa quyết định review vào proposal_hash để tránh hash vòng.
Không tạo `target_version_id` có ý nghĩa runtime cho draft còn UNKNOWN; nếu cần
preview phải đặt nhãn DRAFT, không dùng làm accepted target. Khi đủ cấu trúc mới
tính version bằng hàm của repo và adjudicate chính version đó.

`original_issue_ids` là sorted unique list chứa mọi issue mà operation định resolve.
Không ghép ID condition/object thành ID mới thay thế. Field diff giới hạn theo
allowlist explicit, không áp dụng patch ngoài proposal đã duyệt.

## 2. Evidence bundle và completeness

Mỗi source có raw SHA256, source_ref, extractor ID/version/config, locator tuple,
exact raw quote, context spans và dependency/cross-reference nếu có.
`field_support_map` nối từng quantity, unit, operator, condition leaf/operator,
exception, scope và jurisdiction/legal-status assertion tới support spans cụ thể.

Hash verified không chứng minh ngữ nghĩa. `completeness_assessments` ghi:

- quantity: DRAFT / SUPPORTED / UNKNOWN;
- conditions: DRAFT / SUPPORTED / UNKNOWN;
- exceptions: UNKNOWN / EVIDENCE_BACKED / NO_APPLICABLE_EXCEPTION_IN_REVIEWED_SCOPE;
- applicability, jurisdiction, legal_status: SUPPORTED / UNKNOWN;
- overlap: NO_CONFLICT_IN_REVIEWED_SCOPE / EVIDENCE_BACKED_PRECEDENCE / UNRESOLVED;
- reviewed_scope: sections/pages/cross-references đã kiểm, giới hạn rõ ràng.

Không đánh giá exception=FALSE là SUPPORTED chỉ vì dữ liệu cũ là FALSE. Không coi
UNRESOLVED + quantity đã typed là complete record. Support status chỉ được chấp nhận
để APPLY nếu có adjudication từ trust root thật xác nhận đủ checklist.

Nếu một field không áp dụng, cần policy được phê duyệt và lý do N/A có scope;
không dùng N/A như cách bỏ qua thiếu evidence.

## 3. Contract activation receipt

```text
ContractActivation
  contract_spec_hash
  activation_id / issuer_id / issuer_role
  decision: APPROVE_LOCAL_SHADOW
  allowed_predicates[] / target_entity_ids[]
  mode: LOCAL_SHADOW
  valid_from / valid_until
  approval_evidence_ref / registry_hash
```

Chỉ receipt có issuer hợp lệ mới kích hoạt xử lý ACCEPT của dữ liệu REPOSITORY.
Vai trò này duyệt contract phần mềm, không chứng nhận kiến thức kỹ thuật. Người
duyệt semantic record có vai trò/scope riêng. Một người có thể có cả hai vai trò
nếu registry thực tế cho phép; không tự suy ra quyền đó.

Thay spec hash, predicate hoặc entity allowlist làm activation cũ không đủ hiệu lực.
Không lấy activation từ template DRAFT hoặc biến `enabled=true` do model tự tạo.

## 4. Complete-record adjudication

```text
RecordAdjudication
  proposal_hash / contract_spec_hash
  entity_id / base_version_id / target_version_id
  original_issue_ids[] / source_coverage_hash
  reviewer_id / registry_hash / decided_at
  decision: ACCEPT | REJECT | HOLD | NEEDS_MORE_EVIDENCE
  rationale
  checks: source, quantity, condition_logic, exceptions, applicability,
          jurisdiction, legal_status, overlap, no_omitted_requirements
```

Chỉ ACCEPT với tất cả checks hợp lệ và đúng identity mới dùng để APPLY projection.
Đây không phải Notion publication Decision. Thay bất kỳ thành phần bound nào phải
review lại; không tái bind receipt cũ vào version mới bằng code.

## 5. Dispatcher

```text
dispatch(route, input, independent_trust_roots):
  route == legacy_literal/v1:
      call unchanged V16.2 validator
  route == complete_record_derivation/v1:
      validate contract pin and activation scope
      validate complete record bundle, current base state and adjudication
      validate no unresolved component/new blocker
      stage one entity-level update in a LOCAL projection
      resolve declared original issues atomically in projected ledger
      run independent extension gates
  otherwise:
      UNKNOWN_CONTRACT (fail closed)
```

Không gọi dispatcher mới tự động sau khi legacy thất bại. TEST_ONLY và REPOSITORY
phải tách rõ cả receipts, sources, fixture IDs và eligibility outputs.

Nếu chưa có activation/adjudication thật, đường PROPOSE vẫn chạy, synthetic APPLY
vẫn kiểm thử, còn real APPLY xuất NOT_EXECUTED với lý do. Đây không phải blocker
để bỏ dở việc implement code đã được giao.

## 6. Atomicity và ledger

Một operation bao phủ full semantic change cho một entity. Record/version before
và danh sách blockers phải khớp snapshot hiện hành. Commit projection chỉ khi mọi
validation đã đạt; simulate failure giữa các bước phải rollback toàn bộ projection.

Lưu derived resolution events với original_issue_id, original before hash,
target version và receipt hash. Legacy files giữ nguyên bytes. New blockers có ID
deterministic, root cause/source và `discovered_from` liên kết về record/issue cũ.

Không reuse RESOLVED để che pending human decision. Báo data remediation, publication
decision hiệu lực và runtime authorization riêng. Không có resolved_count tối thiểu
bắt buộc cho real run khi reviewer hoặc source còn thiếu.

## 7. Lỗi cần phân biệt

BASELINE_MISMATCH; SOURCE_UNAVAILABLE; SOURCE_HASH_MISMATCH; LOCATOR_BASE_AMBIGUOUS;
CONDITION_EVIDENCE_INCOMPLETE; EXCEPTION_COVERAGE_UNKNOWN; RULE_OVERLAP_UNRESOLVED;
LEGAL_STATUS_UNVERIFIED; COMPOUND_CLAIM_NOT_REPRESENTABLE; CONTRACT_NOT_ACTIVATED;
REVIEW_REQUIRED; REVIEW_BINDING_STALE; BASE_VERSION_CHANGED; ISSUE_SET_CHANGED;
UNKNOWN_CONTRACT; TEST_DATA_IN_REPOSITORY; ATOMIC_PROJECTION_FAILED.

Các lỗi data/review giữ record blocked với artifact chẩn đoán; các lỗi integrity
không được chuyển thành một route ít nghiêm ngặt hơn. Publication luôn disabled.
