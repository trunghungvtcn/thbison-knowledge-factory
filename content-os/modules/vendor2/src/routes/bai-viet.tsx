import { createFileRoute, Link } from "@tanstack/react-router";
import { Shell, StatusPill } from "@/components/shell";
import { loadArticles } from "@/lib/content-os/workspace.functions";

export const Route = createFileRoute("/bai-viet")({
  loader: () => loadArticles(),
  component: ArticlesPage,
});

function ArticlesPage() {
  const articles = Route.useLoaderData();
  return (
    <Shell>
      <h1 className="font-display text-3xl font-semibold tracking-tight">Bài viết</h1>
      <p className="mt-2 text-muted">Mỗi revision bất biến. Sửa nội dung hoặc SEO tạo revision mới.</p>
      {articles.length === 0 ? (
        <p className="mt-8 text-muted">Chưa có bản nháp. Mở brief mẫu rồi bấm tạo bản nháp.</p>
      ) : (
        <ul className="mt-6 grid gap-3">
          {articles.map((a) => (
            <li key={`${a.article_id}-${a.article_revision}`} className="rounded-lg bg-panel p-4 shadow-[var(--shadow-border)]">
              <div className="flex flex-wrap items-center gap-2">
                <Link className="font-medium hover:underline" to="/bai-viet/$articleId" params={{ articleId: a.article_id }}>
                  {a.title}
                </Link>
                <StatusPill status={a.status} />
                <span className="text-xs text-muted">rev {a.article_revision}</span>
              </div>
              <p className="mt-1 font-mono text-xs text-muted">{a.content_sha256.slice(0, 16)}…</p>
            </li>
          ))}
        </ul>
      )}
    </Shell>
  );
}
