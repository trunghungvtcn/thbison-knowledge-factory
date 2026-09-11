# Ma trận nghiệm thu cho Codex triển khai

Đây là yêu cầu phải viết/chạy trong repo, không phải danh sách test đã PASS.

| ID | Tình huống | Kết quả yêu cầu |
|---|---|---|
| A01 | Baseline/hash/source hoặc code manifest lệch | Real path dừng; không ghi lại pin để pass |
| A02 | Full repo suite trước/sau | Chạy thực tế, báo count/pass/fail |
| A03 | Legacy whole-literal nhận prose-to-scalar cũ | Vẫn V162_CONTRACT_INCOMPATIBLE |
| A04 | Unknown route hoặc implicit fallback | Fail closed |
| A05 | Extension draft chưa có activation | PROPOSE chạy; real APPLY bị chặn |
| A06 | Activation hash/scope/time/issuer sai | Chặn APPLY |
| A07 | Fixture activation/reviewer vào REPOSITORY | Chặn |
| A08 | Quantity hợp lệ, condition UNRESOLVED | Không complete, không resolve toàn record |
| A09 | Condition hợp lệ, exception chưa được rà soát | Không complete |
| A10 | exception FALSE được kế thừa thiếu evidence | EXCEPTION_COVERAGE_UNKNOWN |
| A11 | Cắt nguồn làm mất điều kiện/ngoại lệ | Chặn hoặc yêu cầu thêm context |
| A12 | Lấy số con trong số lớn; unit/operator sai | Chặn |
| A13 | Page ordinal/index/printed label khác nhau | Mapper explicit, tái xác minh raw |
| A14 | Dấu chấm phẩy/list tags không chứng minh connective | Không tự chọn AND/OR |
| A15 | Các atomic predicates/AST group thiếu support | Chặn complete |
| A16 | Rule overlap/priority không có evidence | Blocker được ghi nhận, không tự ưu tiên |
| A17 | inherited legal-status/applicability thiếu căn cứ | Ghi UNKNOWN, không certify bằng copy |
| A18 | Compound claim -> một scalar làm mất nghĩa | HOLD; không resolve một phần rồi che phần còn lại |
| A19 | Object + condition sửa cùng primary | Một target version, giữ entity/page/parent |
| A20 | Một adjudication quantity cũ + adjudication condition khác | Không hợp thành approval whole-record |
| A21 | Target version/issue set/source coverage thay sau review | Review stale |
| A22 | Missing/untrusted/self reviewer | Chặn ACCEPT |
| A23 | Current base version đổi sau dựng proposal | Chặn projection; cần recompute/review |
| A24 | Atomic apply fail giữa object và condition | Không issue nào bị resolve một phần |
| A25 | Primary có thêm blocker mới | Tăng ledger mới có lineage; record vẫn blocked |
| A26 | Original 79 + new blockers | Accounting công thức đúng; không hard-code total |
| A27 | Current HOLD/REJECTED/notes mới | Human state giữ ưu tiên, notes không bị ghi |
| A28 | Other 69 records | Không thay semantic/version/mapping khi primary là target duy nhất |
| A29 | Reverse order records/issues/spans | Semantic output deterministic; input byte pins báo riêng |
| A30 | Final/replay cùng pin/as_of/code | Byte/hash equality |
| A31 | Artifact totals bị sửa và rehash | Independent recomputation phát hiện |
| A32 | Real no-accept run | 0 projected resolutions; original baseline/ledger/mappings giữ nguyên |
| A33 | Synthetic complete-record ACCEPT hợp lệ | Extension projection thành công, TEST_ONLY, không publication |
| A34 | Đường synthetic positive khác validator real | Không được báo chứng minh integration |
| A35 | Mapping thiếu/collision/parent/schema mismatch | Không eligible; không CREATE fallback |
| A36 | Bất kỳ mutation HTTP/SQL/schema/scheduler | Test fail; scope counters 0 |

## Ý nghĩa status

- `V165_HANDOFF_PACK_VERIFIED`: chỉ gói bàn giao và input ZIP được kiểm.
- `V165_CODE_PASS_WAITING_INPUTS / PHASE_F_NOT_AUTHORIZED`: code và tests thật đạt;
  real record còn source/contract/review input thiếu, phải liệt kê chính xác.
- `V165_COMPLETE_RECORD_PROJECTED / PHASE_F_NOT_AUTHORIZED`: ít nhất một record
  thật qua extension gates trong projection local. Không đồng nghĩa publication.
- `V165_BASELINE_OR_INTEGRITY_FAIL`: không tái lập baseline/source/state; không
  thay manifest/gate để sửa số PASS.

Một status không thay thế các counters. Full repository PASS và package verification
phải báo riêng. Không yêu cầu có positive real ACCEPT khi chưa ai duyệt.
