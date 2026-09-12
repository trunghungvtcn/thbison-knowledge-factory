import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, ShieldNote, StatusPill } from "@/components/shell";
import { Button } from "@/components/ui/button";
import { generateDraft, loadBrief, saveBrief } from "@/lib/content-os/workspace.functions";

export const Route = createFileRoute("/ke-hoach_/$briefId")({
  loader: ({ params }) => loadBrief({ data: { briefId: params.briefId } }),
  component: BriefPage,
});

function BriefPage() {
  const { brief, evidence } = Route.useLoaderData();
  const router = useRouter();
  const [title, setTitle] = useState(brief.title);
  const [audience, setAudience] = useState(brief.audience);
  const [primaryKeyword, setPrimaryKeyword] = useState(brief.primary_keyword);
  const [questions, setQuestions] = useState(brief.questions.join("\n"));
  const [outline, setOutline] = useState(brief.outline.join("\n"));
  const [date, setDate] = useState(brief.proposed_publish_at ?? "");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  return (
    <Shell>
      <p className="text-xs text-muted">Brief {brief.brief_id} · rev {brief.brief_revision}</p>
      <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight">{brief.title}</h1>
      <div className="mt-2 flex flex-wrap gap-2">
        <StatusPill status={brief.origin} />
        <StatusPill status={brief.data_class} />
        <StatusPill status="MOCK" />
      </div>
      <form
        className="mt-6 grid gap-4 rounded-lg bg-panel p-5 shadow-[var(--shadow-border)]"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          const next = await saveBrief({
            data: {
              briefId: brief.brief_id,
              title,
              audience,
              primaryKeyword,
              questions: questions.split("\n").map((value) => value.trim()).filter(Boolean),
              outline: outline.split("\n").map((value) => value.trim()).filter(Boolean),
              proposed_publish_at: date ? new Date(date).toISOString() : null,
            },
          });
          setMsg(`Đã lưu revision ${next.brief_revision}. Duyệt bài phụ thuộc brief cũ không còn hiệu lực.`);
          setBusy(false);
          await router.invalidate();
        }}
      >
        <label className="grid gap-1 text-sm">
          Tiêu đề
          <input className="min-h-11 rounded-sm border border-line bg-paper px-3" value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label className="grid gap-1 text-sm">
          Đối tượng
          <input className="min-h-11 rounded-sm border border-line bg-paper px-3" value={audience} onChange={(e) => setAudience(e.target.value)} />
        </label>
        <label className="grid gap-1 text-sm">
          Từ khóa chính
          <input className="min-h-11 rounded-sm border border-line bg-paper px-3" value={primaryKeyword} onChange={(e) => setPrimaryKeyword(e.target.value)} />
        </label>
        <label className="grid gap-1 text-sm">
          Ngày đề xuất (không phải lệnh xuất bản)
          <input
            type="datetime-local"
            className="min-h-11 rounded-sm border border-line bg-paper px-3"
            value={date ? date.slice(0, 16) : ""}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
        <label className="grid gap-1 text-sm">Câu hỏi mục tiêu · mỗi dòng một câu
          <textarea className="min-h-28 rounded-sm border border-line bg-paper px-3 py-2" value={questions} onChange={(e) => setQuestions(e.target.value)} />
        </label>
        <label className="grid gap-1 text-sm">Dàn ý · mỗi dòng một mục
          <textarea className="min-h-36 rounded-sm border border-line bg-paper px-3 py-2" value={outline} onChange={(e) => setOutline(e.target.value)} />
        </label>
        <p className="text-sm text-muted">Phạm vi SEO: {brief.scope.country_code}/{brief.scope.language}</p>
        <ShieldNote />
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={busy}>Lưu revision brief</Button>
          <Button
            type="button"
            variant="secondary"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              const job = await generateDraft({ data: { briefId: brief.brief_id, bundleId: evidence.bundle_id } });
              setMsg(`Job ${job.job_id} · ${job.status}`);
              setBusy(false);
              await router.invalidate();
            }}
          >
            Chuyển brief thành bản nháp
          </Button>
        </div>
        {msg ? <p className="text-sm text-ok">{msg}</p> : null}
      </form>
      <section className="mt-6 rounded-lg bg-panel p-5 shadow-[var(--shadow-border)]">
        <h2 className="text-lg font-semibold">Bằng chứng {evidence.bundle_id}</h2>
        <ul className="mt-3 grid gap-3">
          {evidence.claims.map((c) => (
            <li key={c.claim_id} className="rounded-md bg-paper p-3">
              <div className="flex flex-wrap gap-2">
                <StatusPill status={c.status} />
                <StatusPill status={c.risk} />
              </div>
              <p className="mt-2 text-sm">{c.text}</p>
              <p className="mt-1 font-mono text-xs text-muted">{c.source_ref} · {c.locator}</p>
            </li>
          ))}
        </ul>
      </section>
      <p className="mt-4">
        <Link className="text-sm underline" to="/bai-viet">Xem danh sách bài</Link>
      </p>
    </Shell>
  );
}
