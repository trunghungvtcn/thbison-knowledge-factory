import { createFileRoute } from "@tanstack/react-router";
import { Shell, StatusPill } from "@/components/shell";

const ROWS: Array<{ id: string; owner: string; result: string; note: string }> = [
  { id: "KIT_SELF_TEST", owner: "BOTH", result: "PARTIAL", note: "50 PASS + 1 FAIL (test_naive_date_rejected). Kit không sửa. Không phải nghiệm thu xong." },
  { id: "G01-G12", owner: "BOTH", result: "OFFLINE", note: "Hash/idempotency/auth trên mock — không phải ADAPTER_VERIFIED" },
  { id: "S01-S18", owner: "VENDOR_1", result: "NOT_RUN", note: "Ngoài phạm vi Vendor 2" },
  { id: "C01-C22", owner: "VENDOR_2", result: "OFFLINE", note: "Mock ports. Không tuyên bố đã tích hợp dịch vụ thật." },
  { id: "P05", owner: "BOTH", result: "NOT_MET", note: "Chưa có baseline Vendor 1 trên VPS B. Số liệu preview không phải bằng chứng 15%." },
  { id: "P08", owner: "BOTH", result: "SYNTHETIC", note: "Rehearsal Knowledge/CMS giả lập. Không phải canary." },
  { id: "A1-A8", owner: "ASSEMBLY", result: "BLOCKED_EXTERNAL", note: "Thiếu CMS/Knowledge/OpenSEO scoped thật" },
];

export const Route = createFileRoute("/nghiem-thu")({
  component: AcceptancePage,
});

function AcceptancePage() {
  return (
    <Shell>
      <h1 className="font-display text-3xl font-semibold tracking-tight">Cổng nghiệm thu</h1>
      <p className="mt-2 max-w-2xl text-muted">
        Không gộp nhãn. KIT_SELF_TEST đang PARTIAL — đây không phải nghiệm thu hoàn tất.
        KIT_SELF_TEST_PASS ≠ OFFLINE_VERIFIED ≠ ADAPTER_VERIFIED. Kết quả mô phỏng không được gọi là tích hợp thành công.
      </p>
      <div className="mt-6 rounded-lg bg-panel p-4 shadow-[var(--shadow-border)]">
        <p className="font-medium">Gói phát hành cho đội nội bộ tái kiểm tra</p>
        <p className="mt-1 text-sm text-muted">
          Trạng thái <span className="font-mono">CHANGES_ADDRESSED_MOCK</span>. Không tuyên bố nghiệm thu xong.
        </p>
        <div className="mt-3 flex flex-wrap gap-3 text-sm">
          <a className="underline" href="/THBISON-VENDOR-2-CONTENT-WORKFLOW.zip" download>
            Tải ZIP phát hành
          </a>
          <a className="underline" href="/THBISON-VENDOR-2-CONTENT-WORKFLOW.zip.sha256" download>
            SHA256 sidecar (digest của ZIP)
          </a>
          <a className="underline" href="/RELEASE_MANIFEST.json">
            RELEASE_MANIFEST.json
          </a>
          <a className="underline" href="/DELIVERY_RECEIPT.json">
            DELIVERY_RECEIPT.json
          </a>
        </div>
      </div>
      <ul className="mt-6 grid gap-3">
        {ROWS.map((r) => (
          <li key={r.id} className="rounded-lg bg-panel p-4 shadow-[var(--shadow-border)]">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-sm">{r.id}</span>
              <StatusPill status={r.result} />
              <span className="text-xs text-muted">{r.owner}</span>
            </div>
            <p className="mt-2 text-sm">{r.note}</p>
          </li>
        ))}
      </ul>
    </Shell>
  );
}
