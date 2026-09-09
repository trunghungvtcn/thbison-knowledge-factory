# Mẫu báo cáo thực thi V16.5

Chỉ điền sau khi chạy tại repo thật. Không lấy số từ report mẫu làm kết quả.

```text
Status:
Mode: LOCAL / NO_WRITE
Commit / working-tree patch reference:
Input manifests / as_of:
V16.1 baseline before / after:
Full repository tests before / after:
Legacy V16.2/V16.3/V16.4 gates:
Extension contract ID/hash / activation status:
Primary entity / base version / target version:
Source byte verification / page mapper verification:
Quantity / condition / exception completeness:
Applicability / jurisdiction / legal-status support:
Cross-rule overlap / precedence evidence:
Contract receipts valid / missing:
Semantic adjudications ACCEPT / REJECT / HOLD / NEEDS_MORE_EVIDENCE:
Original unresolved issues:
Original issues resolved in projection:
New blockers discovered / unresolved:
Total projected unresolved:
Complete records projected:
Publication review effective / stale / missing:
Eligible production / canary records (computed only if gates actually executed):
authorized_to_execute: false
Unrelated record deltas:
Human-field writes / production writes / CREATE / SQL / schema / scheduler:
Legacy baseline/ledger/source/mapping hashes unchanged:
Independent recomputation / final-replay byte equality:
Artifact hashes:
Remaining blockers with exact missing evidence/receipt:
```

## Artifacts yêu cầu

Mỗi run output directory mới, ví dụ `v165/artifacts/final-001` và `replay-001`:

- baseline_verification.json
- source_coverage.json
- field_support_map.json
- rule_overlap_review.json
- contract_spec.json và contract_activation_status.json
- complete_record_proposals.jsonl
- review_pack.md và adjudications.jsonl (rỗng nếu chưa có)
- projection_events.jsonl
- original_issue_lineage.jsonl
- new_blockers.jsonl
- projected_issue_ledger.json
- projected_record_plan.json
- readiness_report.json
- phase_f_canary_plan.json (không executable)
- input_manifest.json, code_manifest.json, artifact_hashes.json

Artifact của bước chưa chạy phải ghi NOT_EXECUTED và lý do, không điền 0 rồi
ngụ ý đã kiểm chứng. Counters ghi thực tế; với bước không thực thi phải tách rõ N/A.
Nếu scope yêu cầu 0 mutation, ghi số đo/test spy tương ứng thay vì flag cấu hình.
