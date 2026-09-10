# Acceptance Matrix — Vendor 4

| ID | Tình huống | Kết quả bắt buộc |
|---|---|---|
| K01 | Query đúng scope | EvidenceBundle schema-valid |
| K02 | Wrong project/product/model | 403 hoặc empty có reason |
| K03 | Wrong jurisdiction | Không trả claim ngoài phạm vi |
| K04 | HOLD claim | Loại/block rõ ràng |
| K05 | REVOKED source | Loại và invalidate cache |
| K06 | Stale source | Freshness state rõ ràng |
| K07 | Quote tampering | Hash mismatch bị chặn |
| K08 | Missing locator | Không đủ điều kiện bundle |
| K09 | Duplicate claim/version | Deterministic dedupe |
| K10 | Condition conflict | HOLD/blocker, không tự chọn AND/OR |
| K11 | Ranking replay | Cùng input cho cùng thứ tự/score |
| K12 | Ranking benchmark | So baseline và ghi PROMOTE/NO_IMPROVEMENT |
| K13 | Upload synthetic asset | Pending receipt trước complete |
| K14 | Timeout after accept | Reconcile, không upload trùng |
| K15 | Signed URL expired | Refresh URL, giữ identity |
| K16 | Download hash mismatch | Chặn complete/read |
| K17 | Duplicate upload | Một logical asset |
| K18 | Basename collision | Không overwrite |
| K19 | Path traversal/symlink escape | Từ chối |
| K20 | 429 Retry-After | Retry bounded đúng chỉ dẫn |
| K21 | Cache same revision | Hit đúng project/scope |
| K22 | New revision | Cache cũ không được dùng |
| K23 | Revoke after cache | Lần đọc sau bị chặn |
| K24 | Unknown write field | Fail closed |
| K25 | Human-managed field write | Bị từ chối |
| K26 | Restart pending upload | Blob/ledger còn và reconcile được |
| K27 | Cross-project asset read | 403 |
| K28 | Malicious source text | Dữ liệu không trở thành instruction |
| K29 | Internal URL/ID scan | 0 hit trong release |
| K30 | Synthetic integration | Vendor 2 consumer đọc bundle thành công |
| K31 | Source/schema mapping | Mapping pin revision, không hardcode ID thật |
| K32 | Staging read round-trip | Đọc đúng scope/revision |
| K33 | Staging write round-trip | Chỉ field allowlist/namespace test |
| K34 | Staging mutation receipt | 100% mutation có run ID |
| K35 | Cleanup/rollback | Delta ngoài namespace = 0 |
| K36 | Production credential/endpoint | Bị từ chối tuyệt đối |

Production adapter/canary phải ghi `OUT_OF_SCOPE`, không ghi PASS. Staging compatibility chỉ PASS khi có revision và receipt.
