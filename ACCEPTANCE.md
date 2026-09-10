# Gates cố định
G0 Integrity/provenance: mọi input đúng pin, conflicts có giải thích, license giữ lại.
G1 Clean install/typecheck/build V1/V2 thành công; isolated DB migration thành công.
G2 J1 strict thiếu/hash mismatch trả nonzero, PRESENT≠HASH_VERIFIED, hash inventory tái hiện trên đúng source/tool. Không dùng git hash-object thay sha256sum.
G3 J2 full collection accounting: executed + NOT_RUN giải thích đầy đủ; 6 test dữ liệu ngoài Git không biến thành PASS. Thêm bridge tests vào lệnh verify, thiếu package phải fail.
G4 Bridge B1–B4: hold trước effects; exact offline transport; lỗi envelopes không complete; receipt hash đối chiếu ledger; crash sau projection/trước receipt không false replay success; synthetic≠real.
G5 Actual processes V1→V2→V3→V4→V5 với V6 quan sát: brief/article ID, revision, project, evidence digest và approval binding đúng; CMS DRY_RUN.
G6 Restart/retry: DB read-back sau restart, không duplicate job/publication; timeout/cancel rõ; evidence thiếu hoặc approval sai bị chặn.
G7 UI: tạo plan/brief, draft, preview; auth tenant/project boundary; screenshot desktop/mobile; không yêu cầu redesign.
G8 Knowledge gateway: mapping từ local Knowledge output/fixture xác định được sang EvidenceBundle. Ghi rõ phạm vi mô phỏng; real knowledge còn blocker.
G9 Notion read-only chỉ target sandbox explicit; không có target→NOTION_TARGET_MISSING. Không chặn G0–G8.
G10 Public packaging không secrets/corpus/private snapshots; Release asset hash tải lại đúng; Grok độc lập không dựa report Codex để PASS.
Verdicts: SIMULATION_PASS chỉ khi G0–G8 đạt trong scope thực chạy; HANDOFF_WITH_BLOCKERS nếu chưa đạt; live_data_pass=false nếu G9/input chưa đủ. Không có production verdict trong job.
