import { createFileRoute } from "@tanstack/react-router";
import { Shell, StatusPill } from "@/components/shell";
import { loadHistory } from "@/lib/content-os/workspace.functions";

export const Route = createFileRoute("/lich-su")({
  loader: () => loadHistory(),
  component: HistoryPage,
});

function HistoryPage() {
  const { jobs, pubs } = Route.useLoaderData();
  return (
    <Shell>
      <h1 className="font-display text-3xl font-semibold tracking-tight">Lịch sử chạy</h1>
      <p className="mt-2 text-muted">Không log token, signed URL hay ghi chú nội bộ.</p>
      <h2 className="mt-6 text-lg font-semibold">Jobs</h2>
      <ul className="mt-3 grid gap-2">
        {jobs.map((j) => (
          <li key={j.job_id} className="flex flex-wrap items-center gap-2 rounded-md bg-panel p-3 text-sm shadow-[var(--shadow-border)]">
            <StatusPill status={j.status} />
            <span className="font-mono text-xs">{j.job_id}</span>
            <span>{j.kind}</span>
            {j.error_code ? <span className="text-danger">{j.error_code}</span> : null}
            <span className="text-xs text-muted">calls {j.provider_requests} · {j.cost_usd} USD</span>
          </li>
        ))}
      </ul>
      <h2 className="mt-8 text-lg font-semibold">Publication receipts</h2>
      <ul className="mt-3 grid gap-2">
        {pubs.map((p) => (
          <li key={p.publication_id} className="rounded-md bg-panel p-3 text-sm shadow-[var(--shadow-border)]">
            <StatusPill status={p.status} />
            <p className="mt-1 font-mono text-xs">{p.publication_id}</p>
            <p className="text-xs text-muted">side-effects {p.actual_side_effects} · {p.destination_id}</p>
          </li>
        ))}
      </ul>
    </Shell>
  );
}
