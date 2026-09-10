import { useCallback, useEffect, useState } from "react";
import { LoaderCircle, ShieldAlert, Workflow } from "lucide-react";

type JobReceipt = {
  job_id: string;
  status: string;
  request_id: string;
  error_code: string | null;
  result_artifact: { sha256: string; bytes: number } | null;
};

type Keyword = {
  keyword: string;
  volume: number | null;
  difficulty: number | null;
  measurement_status: string;
  captured_at: string;
  provider: string;
};

type Brief = {
  brief_id: string;
  brief_revision: number;
  title: string;
  audience: string;
  intent: string;
  primary_keyword: string;
  secondary_keywords: string[];
  questions: string[];
  outline: string[];
  evidence_requirements: string[];
  editorial_constraints: string[];
  proposed_publish_at: string | null;
  origin: string;
};

type Output = {
  research: { research_id: string; keywords: Keyword[]; warnings: string[]; scope: { country_code: string; language: string } };
  brief: Brief;
};

const H = (token: string) => ({
  authorization: `Bearer ${token}`,
  "content-type": "application/json",
  "x-contract-version": "1.0.0",
});

async function pollOutput(token: string, jobId: string): Promise<Output> {
  for (let i = 0; i < 40; i++) {
    const st = await fetch(`/v1/planning/jobs/${jobId}`, { headers: H(token) });
    const rec = (await st.json()) as JobReceipt & { code?: string };
    if (rec.status === "SUCCEEDED") {
      const o = await fetch(`/v1/planning/jobs/${jobId}/output`, { headers: H(token) });
      if (!o.ok) throw new Error("output " + o.status);
      return (await o.json()) as Output;
    }
    if (["FAILED", "CANCELLED", "BUDGET_EXHAUSTED", "TIMED_OUT"].includes(rec.status)) {
      throw new Error(rec.error_code ?? rec.status);
    }
    await new Promise((r) => setTimeout(r, 120));
  }
  throw new Error("timeout waiting for job");
}

export function PlanningConsole(props: { token: string; modeLabel: string; contract: string }) {
  const [goal, setGoal] = useState("Nội dung kỹ thuật pa lăng xích kéo tay cho thị trường Việt Nam");
  const [seeds, setSeeds] = useState("pa lăng xích kéo tay\ncấu tạo pa lăng xích\nmua pa lăng xích kéo tay");
  const [pages, setPages] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [output, setOutput] = useState<Output | null>(null);
  const [caps, setCaps] = useState<Record<string, unknown> | null>(null);
  const [health, setHealth] = useState("…");
  const [calendar, setCalendar] = useState("");
  const [publishCalls, setPublishCalls] = useState(0);

  useEffect(() => {
    void fetch("/healthz")
      .then((r) => r.json())
      .then((j: { status: string }) => setHealth(j.status))
      .catch(() => setHealth("down"));
    void fetch("/v1/capabilities", { headers: H(props.token) })
      .then((r) => r.json())
      .then(setCaps)
      .catch(() => setCaps(null));
  }, [props.token]);

  const run = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const existing_pages = pages
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean)
        .map((line, i) => {
          const [title, url, intent] = line.split("|").map((s) => s.trim());
          return {
            page_id: `page-${i + 1}`,
            url: url || "https://example.invalid/pilot",
            title: title || line,
            intent: intent || "informational",
          };
        });
      const body = {
        contract_version: "1.0.0",
        project_id: "test-thbison",
        data_class: "TEST_ONLY",
        request_id: "req-" + Math.random().toString(36).slice(2, 12).padEnd(10, "0"),
        scope: {
          country_code: "VN",
          language: "vi",
          timezone: "Asia/Bangkok",
          domain: "manual-chain-hoist",
        },
        seeds: seeds
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        existing_pages,
        budget: {
          max_provider_requests: 4,
          max_tokens: 2000,
          max_cost_usd: "0.500000",
          deadline_at: "2030-01-01T00:30:00Z",
          max_transport_attempts: 2,
        },
      };
      const idem = "idem-" + Date.now().toString(16).padStart(16, "0");
      const headers: Record<string, string> = { ...H(props.token), "Idempotency-Key": idem };
      if (calendar) headers["x-thbison-proposed-publish-at"] = calendar;
      const res = await fetch("/v1/planning/jobs", { method: "POST", headers, body: JSON.stringify(body) });
      const rec = (await res.json()) as JobReceipt & { message?: string; code?: string };
      if (!res.ok) throw new Error(rec.message ?? rec.code ?? String(res.status));
      const out = await pollOutput(props.token, rec.job_id);
      setOutput(out);
      const c = await fetch("/v1/meta/counters", { headers: H(props.token) });
      const cj = (await c.json()) as { counters: { publish_calls: number } };
      setPublishCalls(cj.counters.publish_calls);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [calendar, pages, props.token, seeds]);

  const reviseCalendar = useCallback(async () => {
    if (!output) return;
    setBusy(true);
    try {
      const res = await fetch(`/v1/briefs/${output.brief.brief_id}`, {
        method: "POST",
        headers: { ...H(props.token), "Idempotency-Key": "revise-calendar-0001" },
        body: JSON.stringify({
          brief_revision: output.brief.brief_revision,
          proposed_publish_at: calendar || null,
        }),
      });
      const b = (await res.json()) as Brief & { message?: string };
      if (!res.ok) throw new Error(b.message ?? "revise failed");
      setOutput({ ...output, brief: b });
      const c = await fetch("/v1/meta/counters", { headers: H(props.token) });
      const cj = (await c.json()) as { counters: { publish_calls: number } };
      setPublishCalls(cj.counters.publish_calls);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [calendar, output, props.token]);

  return (
    <div className="min-h-screen bg-bg text-fg" data-qa="planning-console">
      <header className="border-b border-border px-4 py-5 sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-medium tracking-wide text-muted uppercase">THBISON · Vendor 1</p>
            <h1 className="font-display mt-1 text-3xl font-medium tracking-tight sm:text-4xl">SEO Planning</h1>
            <p className="mt-2 max-w-xl text-sm text-muted">
              Adapter OpenSEO → quan sát đã chuẩn hoá → cụm intent → ContentBrief. Lịch đề xuất không phải lệnh xuất bản.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-full border border-border bg-surface px-3 py-2">health {health}</span>
            <span className="rounded-full border border-border bg-surface px-3 py-2">{props.modeLabel}</span>
            <span className="rounded-full border border-border bg-surface px-3 py-2">contract {props.contract}</span>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-6 sm:px-8 lg:grid-cols-[minmax(0,20rem)_1fr]">
        <section className="h-fit rounded-lg border border-border bg-surface p-5">
          <h2 className="text-sm font-medium">Đầu vào nghiên cứu</h2>
          <label className="mt-4 block text-xs text-muted">Mục tiêu</label>
          <textarea
            className="mt-1 min-h-20 w-full rounded-md border border-border bg-bg px-3 py-2 text-sm"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
          />
          <label className="mt-4 block text-xs text-muted">Seed (mỗi dòng một từ khoá)</label>
          <textarea
            className="mt-1 min-h-24 w-full rounded-md border border-border bg-bg px-3 py-2 text-sm"
            value={seeds}
            onChange={(e) => setSeeds(e.target.value)}
          />
          <label className="mt-4 block text-xs text-muted">Trang hiện có (title|url|intent)</label>
          <textarea
            className="mt-1 min-h-16 w-full rounded-md border border-border bg-bg px-3 py-2 text-sm"
            placeholder="Cấu tạo pa lăng xích|https://example.invalid/x|informational"
            value={pages}
            onChange={(e) => setPages(e.target.value)}
          />
          <label className="mt-4 block text-xs text-muted">proposed_publish_at (UTC, tuỳ chọn)</label>
          <input
            className="mt-1 h-11 w-full rounded-md border border-border bg-bg px-3 text-sm"
            placeholder="2030-02-01T00:00:00Z"
            value={calendar}
            onChange={(e) => setCalendar(e.target.value)}
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => void run()}
            className="mt-5 flex h-11 w-full items-center justify-center gap-2 rounded-md bg-accent text-sm font-medium text-accent-fg disabled:opacity-50"
          >
            {busy ? <LoaderCircle className="size-4 animate-spin" /> : <Workflow className="size-4" />}
            Chạy planning
          </button>
          <p className="mt-3 text-xs text-subtle">Locale cố định VN/vi · Asia/Bangkok · domain manual-chain-hoist</p>
        </section>

        <div className="space-y-6">
          {error && (
            <div className="flex gap-3 rounded-lg border border-danger/40 bg-elevated p-4 text-sm">
              <ShieldAlert className="mt-0.5 size-4 shrink-0 text-danger" />
              <p>{error}</p>
            </div>
          )}

          {!output && !error && (
            <div className="rounded-lg border border-dashed border-border p-8 text-sm text-muted">
              Chưa có job. Điền seed tiếng Việt rồi chạy. Metric thiếu sẽ là null, không phải 0. Dữ liệu SYNTHETIC /
              TEST_ONLY.
            </div>
          )}

          {output && (
            <>
              <section className="rounded-lg border border-border bg-surface p-5">
                <h2 className="text-sm font-medium">Keywords · provenance</h2>
                <p className="mt-1 text-xs text-subtle">{output.research.research_id}</p>
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-125 text-left text-sm">
                    <thead className="text-xs text-muted">
                      <tr>
                        <th className="pb-2 font-medium">Keyword</th>
                        <th className="pb-2 font-medium">Volume</th>
                        <th className="pb-2 font-medium">KD</th>
                        <th className="pb-2 font-medium">Status</th>
                        <th className="pb-2 font-medium">Captured</th>
                      </tr>
                    </thead>
                    <tbody>
                      {output.research.keywords.map((k) => (
                        <tr key={k.keyword} className="border-t border-border">
                          <td className="py-2 pr-3">{k.keyword}</td>
                          <td className="py-2 font-mono text-xs">{k.volume === null ? "null" : k.volume}</td>
                          <td className="py-2 font-mono text-xs">{k.difficulty === null ? "null" : k.difficulty}</td>
                          <td className="py-2 text-xs">{k.measurement_status}</td>
                          <td className="py-2 font-mono text-xs text-muted">{k.captured_at}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <ul className="mt-3 list-disc pl-4 text-xs text-muted">
                  {output.research.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </section>

              {output.research.warnings.length > 0 && (
                <section className="rounded-lg border border-border bg-surface p-5">
                  <h2 className="text-sm font-medium">Cảnh báo / cụm</h2>
                  <ul className="mt-3 list-disc pl-4 text-sm text-muted">
                    {output.research.warnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                </section>
              )}

              <section className="rounded-lg border border-border bg-surface p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-medium">ContentBrief r{output.brief.brief_revision}</h2>
                    <p className="mt-1 font-display text-xl">{output.brief.title}</p>
                  </div>
                  <button
                    type="button"
                    className="h-11 rounded-md border border-border px-4 text-sm"
                    onClick={() => void reviseCalendar()}
                    disabled={busy}
                  >
                    Cập nhật lịch (không publish)
                  </button>
                </div>
                <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-xs text-muted">Audience</dt>
                    <dd>{output.brief.audience}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Intent / keyword</dt>
                    <dd>
                      {output.brief.intent} — {output.brief.primary_keyword}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">proposed_publish_at</dt>
                    <dd className="font-mono text-xs">{output.brief.proposed_publish_at ?? "null"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Publish side-effects</dt>
                    <dd className="font-mono text-xs">{publishCalls}</dd>
                  </div>
                </dl>
                <h3 className="mt-4 text-xs font-medium text-muted">Outline</h3>
                <ol className="mt-1 list-decimal pl-5 text-sm">
                  {output.brief.outline.map((o) => (
                    <li key={o}>{o}</li>
                  ))}
                </ol>
                <h3 className="mt-4 text-xs font-medium text-muted">Evidence requirements</h3>
                <ul className="mt-1 list-disc pl-5 text-sm">
                  {output.brief.evidence_requirements.map((o) => (
                    <li key={o}>{o}</li>
                  ))}
                </ul>
              </section>
            </>
          )}

          <section className="rounded-lg border border-border bg-elevated p-5 text-xs text-muted">
            <p>
              OpenSEO pin: every-app/open-seo@3632f408 · MIT · MCP tools discovered: research_keywords,
              get_serp_results. Không copy engine. S02 live probe:{" "}
              {caps ? String((caps as { mode?: string }).mode) : "…"} — thiếu credential thì NOT_RUN_EXTERNAL.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
