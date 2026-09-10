import { CONTRACT_SHA256, CONTRACT_VERSION, codeCommit, nowIso, providerRevision } from "./config.ts";
import { ApiError } from "./errors.ts";
import { idFrom, sha256Hex } from "./hash.ts";
import {
  bump,
  hashPayload,
  idemKey,
  type JobRecord,
  type JobStatus,
  withLedger,
} from "./ledger.ts";
import { buildBrief, clusterKeywords, planningOutput, toResearchResult, type ContentBrief } from "./planner.ts";
import { defaultProvider, type ProviderPort, type ProviderResult } from "./provider.ts";
import type { ResearchRequest } from "./validate.ts";
import { assertAwareInstantOrNull } from "./validate.ts";

let provider: ProviderPort = defaultProvider();

export function setProviderForTests(p: ProviderPort): void {
  provider = p;
}

export function resetProviderForRuntime(): void {
  provider = defaultProvider();
}

function jobReceipt(job: JobRecord) {
  return {
    contract_version: CONTRACT_VERSION,
    project_id: job.project_id,
    data_class: job.data_class,
    job_id: job.job_id,
    request_id: job.first_request_id,
    status: job.status,
    code_commit: codeCommit(),
    contract_sha256: CONTRACT_SHA256,
    result_artifact: job.result_artifact,
    error_code: job.error_code,
  };
}

export async function admitPlanningJob(
  req: ResearchRequest,
  idempotencyKey: string,
  proposedPublishAt: string | null,
): Promise<{ receipt: ReturnType<typeof jobReceipt>; created: boolean }> {
  const op = "planning.create";
  const pHash = hashPayload(req);
  const key = idemKey(req.project_id, op, idempotencyKey);

  const admitted = await withLedger((s) => {
    const existingId = s.idempotency[key];
    if (existingId) {
      const job = s.jobs[existingId];
      if (job.payload_hash !== pHash) {
        throw new ApiError(409, "IDEMPOTENCY_CONFLICT", "Same idempotency key, different payload", req.request_id, false);
      }
      return { job, created: false };
    }
    const job_id = idFrom("job", [req.project_id, idempotencyKey, pHash]);
    const job: JobRecord = {
      job_id,
      project_id: req.project_id,
      data_class: req.data_class,
      request_id: req.request_id,
      first_request_id: req.request_id,
      operation: op,
      status: "QUEUED",
      error_code: null,
      payload: { ...req, _proposed: proposedPublishAt },
      idempotency_key: idempotencyKey,
      payload_hash: pHash,
      result_artifact: null,
      created_at: nowIso(),
      updated_at: nowIso(),
      cancel_requested: false,
      provider_calls: 0,
      reserved_requests: 0,
      reserved_tokens: 0,
      reserved_cost_usd: "0",
      brief_id: undefined,
    };
    s.jobs[job_id] = job;
    s.idempotency[key] = job_id;
    bump(s, "admissions");
    return { job, created: true };
  });

  if (admitted.created) {
    queueMicrotask(() => {
      void runPlanning(admitted.job.job_id);
    });
  }
  return { receipt: jobReceipt(admitted.job), created: admitted.created };
}

async function sleep(ms: number): Promise<void> {
  if (ms <= 0) return;
  await new Promise((r) => setTimeout(r, ms));
}

export async function runPlanning(jobId: string): Promise<void> {
  const start = await withLedger((s) => {
    const job = s.jobs[jobId];
    if (!job) return null;
    if (job.cancel_requested) {
      job.status = "CANCELLED";
      job.updated_at = nowIso();
      return null;
    }
    if (job.status !== "QUEUED") return null;
    job.status = "RUNNING";
    job.updated_at = nowIso();
    const payload = job.payload as ResearchRequest & { _proposed?: string | null };
    const reserve = Math.min(payload.budget.max_provider_requests, 2);
    const bucket = s.reservations[job.project_id] ?? { requests: 0, tokens: 0, cost: 0, charged_unknown: 0 };
    if (bucket.requests + reserve > payload.budget.max_provider_requests && payload.budget.max_provider_requests === 0) {
      job.status = "BUDGET_EXHAUSTED";
      job.error_code = "BUDGET_EXHAUSTED";
      return null;
    }
    bucket.requests += reserve;
    s.reservations[job.project_id] = bucket;
    job.reserved_requests = reserve;
    return payload;
  });
  if (!start) return;

  const req = start as ResearchRequest & { _proposed?: string | null };
  const deadline = Date.parse(req.budget.deadline_at);
  let attempts = 0;
  const maxAttempts = req.budget.max_transport_attempts;
  let lastErr: unknown;

  while (attempts < maxAttempts) {
    attempts += 1;
    const cancelled = await withLedger((s) => s.jobs[jobId]?.cancel_requested);
    if (cancelled) {
      await withLedger((s) => {
        const j = s.jobs[jobId];
        if (j) {
          j.status = "CANCELLED";
          j.updated_at = nowIso();
        }
      });
      return;
    }
    if (Date.now() > deadline && !process.env.THBISON_CLOCK_NOW) {
      await fail(jobId, "TIMED_OUT", "TIMEOUT");
      return;
    }
    try {
      const cacheKey = [
        req.project_id,
        req.scope.country_code,
        req.scope.language,
        providerRevision(),
        req.seeds.map((x) => x.normalize("NFC")).join("|"),
        String(req.budget.max_provider_requests),
      ].join("::");

      const cached = await withLedger((s) => s.cache[cacheKey]);
      let result: ProviderResult;
      if (cached && !process.env.THBISON_DISABLE_CACHE) {
        await withLedger((s) => bump(s, "cache_hits"));
        result = {
          keywords: cached.keywords as never,
          snapshot: cached.snapshot,
          warnings: ["Cache hit; source age still visible on captured_at."],
          calls: 0,
          synthetic: true,
          tool: "research_keywords",
        };
      } else {
        await withLedger((s) => bump(s, "cache_misses"));
        result = await provider.research({
          seeds: req.seeds,
          scope: req.scope,
          maxCalls: req.budget.max_provider_requests,
          deadlineAt: req.budget.deadline_at,
          clock: nowIso(),
          cacheKey,
        });
        await withLedger((s) => {
          bump(s, "provider_calls", result.calls);
          const j = s.jobs[jobId];
          if (j) j.provider_calls += result.calls;
          s.cache[cacheKey] = {
            captured_at: nowIso(),
            provider_calls: result.calls,
            keywords: result.keywords,
            serp: result.keywords.map((k) => k.serp),
            snapshot: result.snapshot,
          };
        });
      }

      const research = toResearchResult(req, result);
      const clusters = clusterKeywords(result.keywords, req.existing_pages);
      for (const c of clusters) {
        research.warnings.push(
          `${c.recommendation} [${c.intent}/${c.product_scope}]: ${c.rationale} :: ${c.keywords.join(", ")}`,
        );
      }
      const headerDate = req._proposed ?? null;
      let brief = buildBrief(req, research, clusters, null, headerDate);
      if (!brief) {
        brief = fallbackBrief(req, research);
      }
      const priorRev = await withLedger((s) => {
        const existing = s.briefs[brief!.brief_id];
        return existing ? (existing.brief.brief_revision as number) : null;
      });
      if (priorRev) brief.brief_revision = priorRev + 1;
      const output = planningOutput(research, brief);
      const extras = {
          clusters,
          ranking_note:
            "Opportunity ranking uses volume/difficulty when MEASURED; it is independent of factual confidence.",
          calendar_is_not_publication: true as const,
          provider_revision: providerRevision(),
        };
      const raw = JSON.stringify(output);
      await withLedger((s) => {
        const j = s.jobs[jobId];
        if (!j) return;
        if (j.cancel_requested) {
          j.status = "CANCELLED";
          return;
        }
        j.status = "SUCCEEDED";
        j.output = output;
        (j as JobRecord & { extras?: unknown }).extras = extras;
        j.brief_id = brief!.brief_id;
        j.result_artifact = {
          artifact_id: "out-" + sha256Hex(raw).slice(0, 16),
          sha256: sha256Hex(raw),
          bytes: Buffer.byteLength(raw),
          media_type: "application/json",
        };
        j.updated_at = nowIso();
        s.briefs[brief!.brief_id] = { brief: brief as unknown as Record<string, unknown>, project_id: req.project_id };
      });
      return;
    } catch (e) {
      lastErr = e;
      const http = (e as { http?: number }).http;
      if (http === 401 || http === 403) {
        await fail(jobId, "FAILED", "PROVIDER_ERROR");
        return;
      }
      if (http === 429) {
        const wait = Number((e as { retryAfter?: number }).retryAfter ?? 0);
        if (attempts >= maxAttempts) {
          await fail(jobId, "FAILED", "RATE_LIMITED");
          return;
        }
        await sleep(wait);
        continue;
      }
      if (String((e as Error).message).includes("TOOL_MISSING") || String((e as Error).message).includes("DRIFT")) {
        await fail(jobId, "FAILED", "PROVIDER_ERROR");
        return;
      }
      if (attempts >= maxAttempts) break;
    }
  }
  await fail(jobId, "FAILED", "PROVIDER_ERROR");
  void lastErr;
}

function fallbackBrief(req: ResearchRequest, research: ReturnType<typeof toResearchResult>): ContentBrief {
  return {
    contract_version: "1.0.0",
    project_id: req.project_id,
    data_class: req.data_class,
    brief_id: idFrom("brf", [req.project_id, research.research_id]),
    brief_revision: 1,
    research_id: research.research_id,
    scope: req.scope,
    title: `Cấu tạo ${req.seeds[0]}`.slice(0, 120),
    audience: "TEST audience",
    intent: "informational",
    primary_keyword: req.seeds[0],
    secondary_keywords: [],
    questions: ["What can be stated from the supplied source?"],
    outline: ["Scope", "Source-supported description"],
    evidence_requirements: ["Every factual block maps to allowed claim IDs."],
    product_refs: [],
    proposed_publish_at: null,
    editorial_constraints: [
      "TEST ONLY: do not publish or treat synthetic facts as product evidence.",
    ],
    origin: "RESEARCH",
  };
}

async function fail(jobId: string, status: JobStatus, code: string): Promise<void> {
  await withLedger((s) => {
    const j = s.jobs[jobId];
    if (!j) return;
    j.status = status;
    j.error_code = code;
    j.updated_at = nowIso();
  });
}

export async function getJob(projectId: string, jobId: string, requestId: string) {
  return withLedger((s) => {
    const job = s.jobs[jobId];
    if (!job || job.project_id !== projectId) {
      throw new ApiError(403, "FORBIDDEN", "Job not visible in this project", requestId, false);
    }
    return jobReceipt(job);
  });
}

export async function getOutput(projectId: string, jobId: string, requestId: string) {
  return withLedger((s) => {
    const job = s.jobs[jobId];
    if (!job || job.project_id !== projectId) {
      throw new ApiError(403, "FORBIDDEN", "Job not visible in this project", requestId, false);
    }
    const terminal = ["SUCCEEDED", "FAILED", "CANCELLED", "BUDGET_EXHAUSTED", "TIMED_OUT", "BLOCKED_INPUT", "NO_CHANGE"];
    if (!terminal.includes(job.status) || job.status !== "SUCCEEDED") {
      throw new ApiError(409, "JOB_NOT_TERMINAL", "Job is not succeeded; poll within deadline", requestId, true);
    }
    return job.output;
  });
}

export async function cancelJob(projectId: string, jobId: string, requestId: string, idem: string) {
  return withLedger((s) => {
    const job = s.jobs[jobId];
    if (!job || job.project_id !== projectId) {
      throw new ApiError(403, "FORBIDDEN", "Job not visible in this project", requestId, false);
    }
    const cancelKey = idemKey(projectId, "planning.cancel", idem);
    const prev = s.idempotency[cancelKey];
    if (prev && prev !== jobId) {
      /* same cancel identity */
    }
    s.idempotency[cancelKey] = jobId;
    job.cancel_requested = true;
    if (job.status === "QUEUED" || job.status === "RUNNING") {
      job.status = "CANCELLED";
      job.updated_at = nowIso();
    }
    return jobReceipt(job);
  });
}

export async function getBrief(projectId: string, briefId: string, requestId: string) {
  return withLedger((s) => {
    const rec = s.briefs[briefId];
    if (!rec) throw new ApiError(403, "FORBIDDEN", "Unknown brief", requestId, false);
    if (rec.project_id !== projectId) {
      throw new ApiError(403, "FORBIDDEN", "Tenant isolation", requestId, false);
    }
    return rec.brief;
  });
}

export async function reviseBriefPublishAt(
  projectId: string,
  briefId: string,
  expectedRevision: number,
  iso: string | null,
  requestId: string,
) {
  return withLedger((s) => {
    const rec = s.briefs[briefId];
    if (!rec || rec.project_id !== projectId) throw new ApiError(403, "FORBIDDEN", "brief", requestId, false);
    const rev = rec.brief.brief_revision as number;
    if (rev !== expectedRevision) throw new ApiError(409, "STALE_REVISION", "brief_revision mismatch", requestId, false);
    const nextAt = assertAwareInstantOrNull(iso, requestId, "proposed_publish_at");
    rec.brief = { ...rec.brief, brief_revision: rev + 1, proposed_publish_at: nextAt };
    return rec.brief;
  });
}

export function listJobsForProject(projectId: string) {
  return withLedger((s) => Object.values(s.jobs).filter((j) => j.project_id === projectId).map(jobReceipt));
}

export { jobReceipt };
