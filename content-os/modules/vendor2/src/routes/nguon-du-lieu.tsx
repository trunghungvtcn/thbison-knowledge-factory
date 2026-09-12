import { Shell, StatusPill } from "@/components/shell";
import { NOTION_DATA_SOURCES } from "@/lib/content-os/notion-policy";
import { useState } from "react";
import { loadNotionSources } from "@/lib/content-os/workspace.functions";
import { createFileRoute } from "@tanstack/react-router";
import { Database, ExternalLink, ShieldCheck } from "lucide-react";

export const Route = createFileRoute("/nguon-du-lieu")({
  loader: () => loadNotionSources(),
  component: NotionSourcesPage,
  pendingComponent: () => <Shell><p role="status">Đang tải nguồn dữ liệu…</p></Shell>,
  errorComponent: ({ reset }) => <Shell><div role="alert">Không tải được snapshot. Không thay bằng dữ liệu mẫu.</div><button className="mt-4 min-h-11 rounded border px-4" onClick={reset}>Thử lại</button></Shell>,
});

const SOURCES = [
  { key: "evidence", id: NOTION_DATA_SOURCES.evidence, label: "Evidence Sources" },
  { key: "products", id: NOTION_DATA_SOURCES.products, label: "Product Attributes" },
  { key: "knowledge", id: NOTION_DATA_SOURCES.knowledge, label: "Knowledge Items" },
] as const;

function NotionSourcesPage() {
  const data = Route.useLoaderData();
  const [query, setQuery] = useState("");
  return (
    <Shell>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Notion · chỉ đọc</p>
          <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight">Nguồn dữ liệu đã kiểm soát</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted">
            Snapshot bất biến từ ba collection được cho phép. Không lưu token Notion và không có thao tác ghi ngược.
          </p>
        </div>
        <span className="inline-flex min-h-9 items-center gap-2 rounded-full bg-ok-bg px-3 text-xs font-medium text-ok">
          <ShieldCheck className="size-4" aria-hidden /> Read-only
        </span>
      </div>

      {!data.available ? (
        <div className="mt-8 rounded-lg bg-panel p-8 shadow-[var(--shadow-border)]">
          <Database className="size-8 text-muted" aria-hidden />
          <h2 className="mt-4 text-lg font-semibold">Chưa có snapshot đã xác minh</h2>
          <p className="mt-2 text-sm text-muted">Runtime giữ fail-closed đến khi operator nhập gói snapshot có checksum hợp lệ.</p>
        </div>
      ) : (
        <>
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {SOURCES.map((source) => (
              <div key={source.id} className="rounded-lg bg-panel p-5 shadow-[var(--shadow-border)]">
                <p className="text-sm font-medium">{source.label}</p>
                <p className="mt-2 font-mono text-3xl tabular-nums">{data.counts[source.key]}</p>
                <p className="mt-2 truncate font-mono text-[11px] text-muted" title={source.id}>{source.id}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 break-all rounded-lg bg-panel px-4 py-3 text-sm text-muted shadow-[var(--shadow-border)]">
            Chụp lúc {data.capturedAt} · nhập lúc {data.importedAt} · SHA-256 <span className="font-mono">{data.snapshotSha256}</span>
          </div>
          <p className="mt-3 text-sm text-muted">Trạng thái dưới đây giữ nguyên từ Notion. Đạt điều kiện trạng thái chưa có nghĩa đã đủ bằng chứng để sinh bài hoặc được phép xuất bản.</p>
          <label className="mt-5 block text-sm font-medium" htmlFor="source-search">Tìm trong nguồn dữ liệu</label>
          <input id="source-search" type="search" value={query} onChange={e => setQuery(e.target.value)} className="mt-2 min-h-11 w-full rounded border border-line bg-panel px-3" placeholder="Tên, trạng thái hoặc phạm vi…" />
          <div className="mt-6 space-y-8">
            {SOURCES.map((source) => {
              const rows = data.rows.filter((row) => row.dataSourceId === source.id && [row.name, row.status, row.decision, row.scope].join(" ").toLocaleLowerCase("vi").includes(query.toLocaleLowerCase("vi").trim()));
              return (
                <section key={source.id} aria-labelledby={`source-${source.key}`}>
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h2 id={`source-${source.key}`} className="text-xl font-semibold">{source.label}</h2>
                    <span className="text-sm text-muted">{rows.length} kết quả · {rows.filter((row) => row.eligible).length} đạt điều kiện trạng thái</span>
                  </div>
                  <div className="overflow-x-auto rounded-lg bg-panel shadow-[var(--shadow-border)]">
                    <table className="w-full min-w-[760px] text-left text-sm">
                      <thead className="border-b border-line bg-raised text-xs text-muted">
                        <tr><th className="px-4 py-3">Tên</th><th className="px-4 py-3">Trạng thái</th><th className="px-4 py-3">Quyết định</th><th className="px-4 py-3">Phạm vi</th><th className="px-4 py-3">Nguồn</th></tr>
                      </thead>
                      <tbody className="divide-y divide-line">
                        {rows.length === 0 && <tr><td colSpan={5} className="px-4 py-6 text-muted">Không có bản ghi phù hợp.</td></tr>}
                        {rows.map((row) => (
                          <tr key={row.recordId}>
                            <td className="px-4 py-3 font-medium">{row.name}</td>
                            <td className="px-4 py-3"><StatusPill status={row.status ?? "UNKNOWN"} /></td>
                            <td className="px-4 py-3">{row.decision ?? "—"}</td>
                            <td className="px-4 py-3 text-muted">{row.scope ?? "—"}</td>
                            <td className="px-4 py-3">
                              {row.sourceUrl ? <a className="inline-flex items-center gap-1 text-steel underline" href={row.sourceUrl} target="_blank" rel="noreferrer">Mở nguồn <ExternalLink className="size-3" aria-hidden /></a> : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              );
            })}
          </div>
        </>
      )}
    </Shell>
  );
}
