import { createFileRoute, Link } from "@tanstack/react-router";
import { Shell, StatusPill } from "@/components/shell";
import { loadOverview } from "@/lib/content-os/workspace.functions";
import { formatBangkok } from "@/lib/content-os/clock";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/")({
  loader: () => loadOverview(),
  component: Home,
});

function Home() {
  const data = Route.useLoaderData();
  return (
    <Shell>
      <div className="mb-6">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Bàn biên tập THBISON</h1>
        <p className="mt-2 max-w-2xl text-muted">
          Một đường đi: brief + bằng chứng → bản nháp gắn nguồn → xem trước → duyệt đúng revision → MOCK draft.
        </p>
      </div>
      <ol className="mb-8 grid gap-3 rounded-lg bg-panel p-4 shadow-[var(--shadow-border)] sm:grid-cols-3">
        <li className="rounded-md bg-paper p-3 text-sm">1. Sửa brief trên Kế hoạch</li>
        <li className="rounded-md bg-paper p-3 text-sm">2. Tạo bản nháp từ fixture</li>
        <li className="rounded-md bg-paper p-3 text-sm">3. Xem nguồn từng khối</li>
        <li className="rounded-md bg-paper p-3 text-sm">4. Sửa bài — duyệt cũ hết hiệu lực</li>
        <li className="rounded-md bg-paper p-3 text-sm">5. Duyệt revision mới</li>
        <li className="rounded-md bg-paper p-3 text-sm">6. Tạo một MOCK draft (DRY_RUN)</li>
      </ol>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Mục tiêu / brief" value={data.briefs} />
        <Stat label="Bản nháp" value={data.drafts} />
        <Stat label="Job" value={data.jobs} />
        <Stat label="Blocker" value={data.blockers} warn={data.blockers > 0} />
      </div>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <StatusPill status="MOCK" />
        <span className="text-sm text-muted">Dự án {data.projectId} · ngân sách {data.budgetUsd} USD · last sync {formatBangkok(data.lastSync)} (Asia/Bangkok)</span>
      </div>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link to="/ke-hoach">
          <Button>Mở lịch kế hoạch</Button>
        </Link>
        <Link to="/ke-hoach/$briefId" params={{ briefId: "test-brief-1" }}>
          <Button variant="secondary">Brief mẫu pa lăng xích</Button>
        </Link>
      </div>
    </Shell>
  );
}

function Stat({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className="rounded-lg bg-panel p-5 shadow-[var(--shadow-border)]">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-2 font-mono text-3xl tabular-nums ${warn ? "text-danger" : "text-ink"}`}>{value}</p>
    </div>
  );
}
