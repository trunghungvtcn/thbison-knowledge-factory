import { createFileRoute, Link } from "@tanstack/react-router";
import { Shell, StatusPill } from "@/components/shell";
import { loadBriefs } from "@/lib/content-os/workspace.functions";
import { formatBangkok } from "@/lib/content-os/clock";

export const Route = createFileRoute("/ke-hoach")({
  loader: () => loadBriefs(),
  component: PlanningPage,
});

function PlanningPage() {
  const briefs = Route.useLoaderData();
  return (
    <Shell>
      <h1 className="font-display text-3xl font-semibold tracking-tight">Kế hoạch nội dung</h1>
      <p className="mt-2 max-w-2xl text-muted">
        Dữ liệu từ cổng planning (Vendor 1 mock). Đổi ngày đề xuất tạo revision mới — không phải lệnh xuất bản.
      </p>
      <div className="mt-6 overflow-x-auto rounded-lg bg-panel shadow-[var(--shadow-border)]">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3">Chủ đề</th>
              <th className="px-4 py-3">Intent</th>
              <th className="px-4 py-3">Ngày đề xuất (Bangkok)</th>
              <th className="px-4 py-3">Nguồn</th>
              <th className="px-4 py-3">Rev</th>
            </tr>
          </thead>
          <tbody>
            {briefs.map((b) => (
              <tr key={`${b.brief_id}-${b.brief_revision}`} className="border-b border-line last:border-0">
                <td className="px-4 py-3">
                  <Link className="font-medium underline-offset-2 hover:underline" to="/ke-hoach/$briefId" params={{ briefId: b.brief_id }}>
                    {b.title}
                  </Link>
                  <p className="text-xs text-muted">{b.primary_keyword}</p>
                </td>
                <td className="px-4 py-3">{b.intent}</td>
                <td className="px-4 py-3 font-mono text-xs">
                  {b.proposed_publish_at ? formatBangkok(b.proposed_publish_at) : "—"}
                </td>
                <td className="px-4 py-3">
                  <StatusPill status={b.origin} />
                </td>
                <td className="px-4 py-3 tabular-nums">{b.brief_revision}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
