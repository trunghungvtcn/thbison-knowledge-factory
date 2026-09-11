import { createFileRoute, useRouter } from "@tanstack/react-router";
import { Shell, ShieldNote, StatusPill } from "@/components/shell";
import { Button } from "@/components/ui/button";
import { decideArticle, loadArticleWorkspace, publishMock } from "@/lib/content-os/workspace.functions";
import { useState } from "react";

export const Route = createFileRoute("/duyet/$articleId")({
  loader: ({ params }) => loadArticleWorkspace({ data: { articleId: params.articleId } }),
  component: ReviewPage,
});

function ReviewPage() {
  const { article, evidence, approval, social, principal } = Route.useLoaderData();
  const router = useRouter();
  const [msg, setMsg] = useState("");
  const [receipt, setReceipt] = useState<string>("");
  const dest = approval?.destination_id ?? "test-cms";

  return (
    <Shell>
      <h1 className="font-display text-3xl font-semibold tracking-tight">Duyệt và xuất bản</h1>
      <p className="mt-2 text-muted">So khớp đúng revision {article.article_revision}. Staging/live bị khóa trên MOCK.</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <StatusPill status={article.status} />
        {approval ? <StatusPill status={approval.decision} /> : <StatusPill status="DRAFT" />}
        <StatusPill status="MOCK" />
      </div>
      <section className="mt-6 grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg bg-panel p-5 shadow-[var(--shadow-border)]">
          <h2 className="font-semibold">Revision khóa</h2>
          <dl className="mt-3 grid gap-2 text-sm">
            <div>content_sha256: <span className="font-mono text-xs break-all">{article.content_sha256}</span></div>
            <div>evidence: <span className="font-mono text-xs break-all">{article.evidence_snapshot_sha256}</span></div>
            <div>destination: {dest}</div>
            <div>Người duyệt máy chủ: {principal.subject_id} ({principal.can_publish ? "can_publish" : "không được xuất bản"})</div>
          </dl>
          <ShieldNote />
          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              disabled={!principal.can_publish}
              onClick={async () => {
                const rec = await decideArticle({ data: { articleId: article.article_id, decision: "APPROVED", destinationId: dest } });
                setMsg(`Approval ${rec.approval_id}`);
                await router.invalidate();
              }}
            >
              Phê duyệt revision này
            </Button>
            <Button
              variant="danger"
              disabled={!principal.can_publish}
              onClick={async () => {
                await decideArticle({ data: { articleId: article.article_id, decision: "REJECTED", destinationId: dest } });
                setMsg("Đã từ chối");
                await router.invalidate();
              }}
            >
              Từ chối
            </Button>
          </div>
        </div>
        <div className="rounded-lg bg-panel p-5 shadow-[var(--shadow-border)]">
          <h2 className="font-semibold">MOCK draft</h2>
          <p className="mt-2 text-sm text-muted">
            TEST_ONLY chỉ DRY_RUN. Màn hình này không bao giờ tuyên bố LIVE/PUBLISHED khi mock.
          </p>
          <Button
            className="mt-4"
            variant="secondary"
            disabled={!approval || approval.decision !== "APPROVED"}
            onClick={async () => {
              if (!approval) return;
              const pub = await publishMock({ data: { articleId: article.article_id, approvalId: approval.approval_id } });
              setReceipt(`${pub.publication_id} · ${pub.status} · side-effects ${pub.actual_side_effects}`);
              await router.invalidate();
            }}
          >
            Tạo MOCK draft
          </Button>
          {receipt ? <p className="mt-3 font-mono text-xs">{receipt}</p> : null}
          {msg ? <p className="mt-2 text-sm">{msg}</p> : null}
        </div>
      </section>
      <section className="mt-6 rounded-lg bg-panel p-5 shadow-[var(--shadow-border)]">
        <h2 className="font-semibold">Tóm tắt Facebook Page</h2>
        <p className="mt-2 text-sm">{social.text}</p>
        <p className="mt-1 text-xs text-muted">Link: {social.link} · posting={String(social.posting)} (cờ tắt)</p>
      </section>
      <aside className="mt-6 text-sm text-muted">
        Nguồn còn hiệu lực: {evidence.claims.filter((c) => c.status === "ELIGIBLE").length} ELIGIBLE
      </aside>
    </Shell>
  );
}
