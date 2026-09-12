import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { Lightbulb, LoaderCircle, Search } from "lucide-react";
import { Shell, StatusPill } from "@/components/shell";
import { loadBriefs, runPlanning } from "@/lib/content-os/workspace.functions";
import { formatBangkok } from "@/lib/content-os/clock";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/ke-hoach")({
  loader: () => loadBriefs(),
  component: PlanningPage,
});

function PlanningPage() {
  const briefs = Route.useLoaderData();
  const router = useRouter();
  const [seed, setSeed] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Awaited<ReturnType<typeof runPlanning>> | null>(null);
  const [error, setError] = useState("");
  return (
    <Shell>
      <h1 className="font-display text-3xl font-semibold tracking-tight">Kế hoạch nội dung</h1>
      <p className="mt-2 max-w-2xl text-muted">
        Từ ý tưởng đến brief: nhập từ khóa hạt giống, xem tín hiệu phân tích có provenance rồi mở brief để chỉnh sửa. Mọi kết quả hiện tại là TEST_ONLY/SYNTHETIC, không gọi dịch vụ trả phí.
      </p>
      <section className="mt-6 grid gap-5 rounded-lg bg-panel p-5 shadow-[var(--shadow-border)] lg:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.2fr)]">
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            setBusy(true);
            setError("");
            try {
              const next = await runPlanning({ data: { seed } });
              setResult(next);
              await router.invalidate();
            } catch (cause) {
              setError(cause instanceof Error ? cause.message : "Không thể chạy planning.");
            } finally {
              setBusy(false);
            }
          }}
        >
          <div className="flex items-center gap-2"><Lightbulb className="size-5 text-steel" aria-hidden /><h2 className="text-lg font-semibold">Lên ý tưởng bài mới</h2></div>
          <label className="mt-4 grid gap-2 text-sm" htmlFor="seed-keyword">Từ khóa hạt giống
            <input id="seed-keyword" className="min-h-11 rounded-sm border border-line bg-paper px-3" value={seed} onChange={(event) => setSeed(event.target.value)} placeholder="Ví dụ: cách chọn pa lăng xích" required />
          </label>
          <Button className="mt-4 w-full" type="submit" disabled={busy || !seed.trim()}>
            {busy ? <LoaderCircle className="size-4 animate-spin" aria-hidden /> : <Search className="size-4" aria-hidden />}
            Phân tích và tạo brief
          </Button>
          <p className="mt-3 text-xs text-muted">VN/vi · Không ghi OpenSEO · Không xuất bản · Chi phí 0 USD.</p>
          {error ? <p role="alert" className="mt-3 text-sm text-danger">{error}</p> : null}
        </form>
        <div className="rounded-md bg-paper p-4">
          {!result?.output ? <div className="grid min-h-40 place-items-center text-center text-sm text-muted">Nhập một ý tưởng để xem từ khóa, độ khó, cảnh báo trùng nội dung và brief đề xuất.</div> : <>
            <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-semibold">Kết quả phân tích</h2><StatusPill status={result.job.status} /></div>
            <p className="mt-1 text-xs text-muted">{result.output.research.research_id} · {result.output.research.keywords[0]?.measurement_status}</p>
            <div className="mt-4 overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="text-xs text-muted"><tr><th className="pb-2">Từ khóa</th><th className="pb-2">Volume</th><th className="pb-2">KD</th><th className="pb-2">Nguồn</th></tr></thead><tbody>{result.output.research.keywords.map((keyword) => <tr key={keyword.keyword} className="border-t border-line"><td className="py-2 pr-3 font-medium">{keyword.keyword}</td><td>{keyword.volume ?? "—"}</td><td>{keyword.difficulty ?? "—"}</td><td className="text-xs">{keyword.provider}</td></tr>)}</tbody></table></div>
            {result.output.research.warnings.map((warning) => <p key={warning} className="mt-3 text-xs text-warn">{warning}</p>)}
            <Link className="mt-4 inline-flex min-h-11 items-center rounded bg-steel px-4 text-sm font-medium text-steel-fg" to="/ke-hoach/$briefId" params={{ briefId: result.output.brief.brief_id }}>Mở và chỉnh brief đề xuất</Link>
          </>}
        </div>
      </section>
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
