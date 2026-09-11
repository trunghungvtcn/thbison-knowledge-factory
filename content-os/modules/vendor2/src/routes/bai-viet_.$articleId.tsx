import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, ShieldNote, StatusPill } from "@/components/shell";
import { Button } from "@/components/ui/button";
import { loadArticleWorkspace, saveArticleEdit } from "@/lib/content-os/workspace.functions";
import { sanitizeText } from "@/lib/content-os/quality";

export const Route = createFileRoute("/bai-viet_/$articleId")({
  loader: ({ params }) => loadArticleWorkspace({ data: { articleId: params.articleId } }),
  component: EditorPage,
});

function EditorPage() {
  const { article, evidence, approval } = Route.useLoaderData();
  const router = useRouter();
  const [title, setTitle] = useState(article.title);
  const [seoTitle, setSeoTitle] = useState(article.seo.title);
  const [seoDesc, setSeoDesc] = useState(article.seo.description);
  const [blockEdits, setBlockEdits] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");
  const [tab, setTab] = useState<"edit" | "preview" | "history">("edit");

  return (
    <Shell>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs text-muted">{article.article_id} · rev {article.article_revision}</p>
          <h1 className="font-display text-3xl font-semibold tracking-tight">{article.title}</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusPill status={article.status} />
          <StatusPill status="MOCK" />
          {approval ? <StatusPill status={approval.decision} /> : <StatusPill status="DRAFT" />}
        </div>
      </div>
      <div className="mt-4 flex gap-2" role="tablist">
        {(["edit", "preview", "history"] as const).map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            className={`min-h-11 rounded-md px-4 text-sm ${tab === t ? "bg-steel text-steel-fg" : "bg-raised"}`}
            onClick={() => setTab(t)}
          >
            {t === "edit" ? "Soạn" : t === "preview" ? "Xem trước" : "Revision"}
          </button>
        ))}
      </div>

      {tab === "edit" ? (
        <form
          className="mt-6 grid gap-4 lg:grid-cols-[1fr_20rem]"
          onSubmit={async (e) => {
            e.preventDefault();
            const firstEdit = Object.entries(blockEdits)[0];
            const next = await saveArticleEdit({
              data: {
                articleId: article.article_id,
                expectedRevision: article.article_revision,
                title,
                seoTitle,
                seoDescription: seoDesc,
                blockId: firstEdit?.[0],
                blockText: firstEdit?.[1],
              },
            });
            setMsg(`Revision ${next.article_revision}. Duyệt cũ bị thu hồi.`);
            await router.invalidate();
          }}
        >
          <div className="grid gap-4 rounded-lg bg-panel p-5 shadow-[var(--shadow-border)]">
            <label className="grid gap-1 text-sm">
              Tiêu đề
              <input className="min-h-11 rounded-sm border border-line bg-paper px-3" value={title} onChange={(e) => setTitle(e.target.value)} />
            </label>
            {article.blocks.map((b) => (
              <label key={b.block_id} className="grid gap-1 text-sm">
                <span className="flex items-center gap-2">
                  {b.kind}
                  {b.claim_ids.map((id) => (
                    <span key={id} className="rounded-full bg-raised px-2 py-0.5 font-mono text-xs">{id}</span>
                  ))}
                </span>
                <textarea
                  className="min-h-24 rounded-sm border border-line bg-paper p-3"
                  defaultValue={b.text}
                  onChange={(e) => setBlockEdits((m) => ({ ...m, [b.block_id]: e.target.value }))}
                />
              </label>
            ))}
            <label className="grid gap-1 text-sm">
              SEO title
              <input className="min-h-11 rounded-sm border border-line bg-paper px-3" value={seoTitle} onChange={(e) => setSeoTitle(e.target.value)} />
            </label>
            <label className="grid gap-1 text-sm">
              SEO description
              <textarea className="min-h-20 rounded-sm border border-line bg-paper p-3" value={seoDesc} onChange={(e) => setSeoDesc(e.target.value)} />
            </label>
            <ShieldNote />
            <Button type="submit">Lưu revision mới</Button>
            {msg ? <p className="text-sm text-ok">{msg}</p> : null}
          </div>
          <aside className="grid gap-3 self-start rounded-lg bg-panel p-4 shadow-[var(--shadow-border)]">
            <h2 className="font-semibold">Bằng chứng</h2>
            {evidence.claims.map((c) => (
              <div key={c.claim_id} className="rounded-md bg-paper p-3 text-sm">
                <StatusPill status={c.status} />
                <p className="mt-2">{c.quote}</p>
                <p className="mt-1 font-mono text-xs text-muted">{c.source_ref} {c.locator}</p>
              </div>
            ))}
            {article.publication_blockers.length ? (
              <div className="rounded-md bg-warn-bg p-3 text-sm text-warn">
                {article.publication_blockers.map((b) => (
                  <p key={b}>{b}</p>
                ))}
              </div>
            ) : null}
            <Link className="text-sm underline" to="/duyet/$articleId" params={{ articleId: article.article_id }}>
              Sang duyệt / xuất bản
            </Link>
          </aside>
        </form>
      ) : null}

      {tab === "preview" ? (
        <article className="prose-preview mt-6 max-w-3xl rounded-lg bg-panel p-6 shadow-[var(--shadow-border)]">
          <p className="text-xs uppercase tracking-wide text-muted">Xem trước đã render — không phải JSON</p>
          <h2 className="mt-2 text-2xl font-semibold">{article.title}</h2>
          {article.blocks.map((b) =>
            b.kind === "HEADING" ? (
              <h3 key={b.block_id} className="mt-5 text-lg font-semibold" dangerouslySetInnerHTML={{ __html: sanitizeText(b.text) }} />
            ) : (
              <p key={b.block_id} className="mt-3 leading-relaxed">
                <span dangerouslySetInnerHTML={{ __html: sanitizeText(b.text) }} />{" "}
                {b.claim_ids.map((id) => {
                  const c = evidence.claims.find((x) => x.claim_id === id);
                  return c ? (
                    <a key={id} className="text-xs text-steel underline" href={`#src-${id}`}>
                      [{id}]
                    </a>
                  ) : null;
                })}
              </p>
            ),
          )}
          <section className="mt-8 border-t border-line pt-4">
            <h3 className="text-sm font-semibold">Nguồn</h3>
            {evidence.claims.map((c) => (
              <p id={`src-${c.claim_id}`} key={c.claim_id} className="mt-2 text-sm text-muted">
                [{c.claim_id}] {c.quote} — {c.source_ref}
              </p>
            ))}
          </section>
        </article>
      ) : null}

      {tab === "history" ? (
        <div className="mt-6 rounded-lg bg-panel p-5 text-sm shadow-[var(--shadow-border)]">
          <p>Revision hiện tại: {article.article_revision}</p>
          <p className="font-mono text-xs break-all">{article.content_sha256}</p>
          <p className="mt-2">Sửa bất kỳ trường bound nào sẽ thu hồi ApprovalRecord cũ.</p>
        </div>
      ) : null}
    </Shell>
  );
}
