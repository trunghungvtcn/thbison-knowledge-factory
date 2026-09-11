# Ownership & điểm nối
| Producer | Consumer | Contract/port | Tình trạng |
|---|---|---|---|
| V1 Planning | V2 Writer | PlanningOutput.brief → DraftRequest.brief | Preview source nối thử PASS; UI/DB ingress chưa nối |
| V4 Knowledge mock | V2 Writer | EvidenceBundle | Fixture, Knowledge thật gắn sau |
| V2 domain processors | V3 Runtime | setQueuePort / registerProcessor | Cần client/worker bridge durable |
| V2 authoritative approval | V5 CMS | ApprovalRecord / PublishRequest / PublicationReceipt | Cần authority adapter; DRY_RUN only |
| V1–5 processes | V6 Harness | explicit registry clients | Chưa actual process E2E |

V2 giữ UI chính, V1 giữ planning service riêng. Không gộp migrations hai app vào chung schema bằng nối file. DB operational mới riêng, Notion giữ knowledge/staging reference sau. Runtime SQLite volume riêng; config không dùng DATABASE_URL của V2 cho V3.
VPS lab ports gợi ý 18081..18085, bind 127.0.0.1; phải kiểm tra trùng cổng trước. Không coi DNS/template là thông tin VPS đã xác minh.
Knowledge later: khóa identity/project/revision/digest/policy, map source EvidenceBundle tại gateway; content thiếu evidence giữ blocked/review. Không cho approval fixture sử dụng publish thật.
