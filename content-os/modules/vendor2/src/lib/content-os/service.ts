import { getSql } from "@/lib/db";
import {
  CODE_COMMIT,
  CONTRACT_SHA256,
  CONTRACT_VERSION,
  LIVE_FLAGS,
  MOCK_DESTINATION,
} from "./constants";
import { ContractError, requireOk } from "./errors";
import { digest, hashWithout, newId } from "./hash";
import { nowIso } from "./clock";
import { assertProject } from "./authz";
import type { Principal } from "./types";
import {
  kitBrief,
  kitEvidence,
  kitPlanning,
  holdEvidence,
  injectEvidence,
  stagingEvidence,
  stagingBrief,
  manualBrief,
} from "./fixtures";
import { checkArticle, checkBundle, defaultPolicy, gatePublish, sealArticle } from "./gate";
import { generateSyntheticArticle } from "./writer";
import { evaluateArticle } from "./quality";
import { cmsCreateDraft, cmsFind, cmsRead, setCmsFault } from "./cms";
import { putArtifact } from "./artifacts";
import { redactValue, safeLog } from "./redaction";
import { validateDraftRequest, validateHeaderContract, validatePublishRequest, validateResearchRequest } from "./validate";
import { getQueue, registerProcessor } from "./queue";
import { persistLedger } from "./durable";
import type {
  ArticlePackage,
  ApprovalRecord,
  ContentBrief,
  DraftRequest,
  EvidenceBundle,
  JobReceipt,
  PlanningOutput,
  PublicationReceipt,
  PublishRequest,
  ResearchRequest,
} from "./types";

void LIVE_FLAGS;

let seeded = false;

export async function ensureSeed(): Promise<void> {
  if (seeded) return;
  const sql = await getSql();
  const rows = await sql<{ n: number }>`select count(*)::int as n from cos_briefs`;
  if ((rows[0]?.n ?? 0) === 0) {
    await insertBrief(kitBrief);
    await insertBrief(manualBrief);
    await insertBrief(stagingBrief);
    await insertEvidence(kitEvidence);
    await insertEvidence(holdEvidence);
    await insertEvidence(injectEvidence);
    await insertEvidence(stagingEvidence);
    const demo = generateSyntheticArticle(kitBrief, kitEvidence, "art-test-brief-1", 1);
    await insertArticle(demo);
    await persistLedger();
  }
  seeded = true;
}

async function insertBrief(brief: ContentBrief) {
  const sql = await getSql();
  await sql`
    insert into cos_briefs (brief_id, brief_revision, project_id, data_class, body_json)
    values (${brief.brief_id}, ${brief.brief_revision}, ${brief.project_id}, ${brief.data_class}, ${JSON.stringify(brief)})
    on conflict (brief_id, brief_revision) do nothing
  `;
}

async function insertEvidence(bundle: EvidenceBundle) {
  const sql = await getSql();
  await sql`
    insert into cos_evidence (bundle_id, project_id, snapshot_sha256, revoked, body_json)
    values (${bundle.bundle_id}, ${bundle.project_id}, ${bundle.snapshot_sha256}, false, ${JSON.stringify(bundle)})
    on conflict (bundle_id) do nothing
  `;
}

async function insertArticle(article: ArticlePackage) {
  const sql = await getSql();
  await sql`
    insert into cos_articles (
      article_id, article_revision, project_id, data_class, brief_id, brief_revision,
      bundle_id, content_sha256, status, expected_revision, body_json
    ) values (
      ${article.article_id}, ${article.article_revision}, ${article.project_id}, ${article.data_class},
      ${article.brief_id}, ${article.brief_revision}, ${article.bundle_id}, ${article.content_sha256},
      ${article.status}, ${article.article_revision}, ${JSON.stringify(article)}
    )
    on conflict (article_id, article_revision) do nothing
  `;
}

export async function admit(
  projectId: string,
  operation: string,
  key: string,
  payload: unknown,
): Promise<{ id: string; fresh: boolean }> {
  requireOk(typeof key === "string" && key.length >= 16 && key.length <= 128, "VALIDATION_ERROR", "Idempotency-Key");
  const sql = await getSql();
  const hash = digest(payload);
  const existing = await sql<{ payload_sha256: string; object_id: string }>`
    select payload_sha256, object_id from cos_idempotency
    where project_id = ${projectId} and operation = ${operation} and key = ${key}
  `;
  if (existing[0]) {
    if (existing[0].payload_sha256 !== hash) throw new ContractError("IDEMPOTENCY_CONFLICT");
    return { id: existing[0].object_id, fresh: false };
  }
  const id = newId(operation.startsWith("pub") ? "pub" : "job");
  try {
    await sql`
      insert into cos_idempotency (project_id, operation, key, payload_sha256, object_id)
      values (${projectId}, ${operation}, ${key}, ${hash}, ${id})
    `;
  } catch {
    const again = await sql<{ payload_sha256: string; object_id: string }>`
      select payload_sha256, object_id from cos_idempotency
      where project_id = ${projectId} and operation = ${operation} and key = ${key}
    `;
    if (again[0]) {
      if (again[0].payload_sha256 !== hash) throw new ContractError("IDEMPOTENCY_CONFLICT");
      return { id: again[0].object_id, fresh: false };
    }
    throw new ContractError("PROVIDER_ERROR", "idempotency insert failed", true);
  }
  return { id, fresh: true };
}

function receipt(
  job: {
    project_id: string;
    data_class: string;
    job_id: string;
    request_id: string;
    status: JobReceipt["status"];
    error_code: string | null;
    result_json: string | null;
  },
): JobReceipt {
  let result_artifact: JobReceipt["result_artifact"] = null;
  if (job.result_json) {
    const sha = digest(JSON.parse(job.result_json));
    result_artifact = {
      artifact_id: `art-${job.job_id}`,
      sha256: sha,
      bytes: Buffer.byteLength(job.result_json, "utf8"),
      media_type: "application/json",
    };
  }
  return {
    contract_version: CONTRACT_VERSION,
    project_id: job.project_id,
    data_class: job.data_class as JobReceipt["data_class"],
    job_id: job.job_id,
    request_id: job.request_id,
    status: job.status,
    code_commit: CODE_COMMIT,
    contract_sha256: CONTRACT_SHA256,
    result_artifact,
    error_code: job.error_code,
  };
}

export async function submitContentJob(
  principal: Principal,
  body: unknown,
  idempotencyKey: string,
  contractVersion: string,
): Promise<JobReceipt> {
  await ensureSeed();
  validateHeaderContract(contractVersion);
  const req = validateDraftRequest(body) as unknown as DraftRequest;
  assertProject(principal, req.project_id);
  const { id, fresh } = await admit(req.project_id, "content.draft", idempotencyKey, req);
  const sql = await getSql();
  if (!fresh) {
    const rows = await sql<Parameters<typeof receipt>[0]>`
      select project_id, data_class, job_id, request_id, status, error_code, result_json
      from cos_jobs where job_id = ${id}
    `;
    if (rows[0]) return receipt(rows[0]);
  }
  await sql`
    insert into cos_jobs (job_id, project_id, data_class, request_id, kind, status, payload_json, deadline_at)
    values (${id}, ${req.project_id}, ${req.data_class}, ${req.request_id}, ${"content"}, ${"QUEUED"}, ${JSON.stringify(req)}, ${req.budget.deadline_at})
  `;
  await persistLedger();
  const queued = receipt({
    project_id: req.project_id,
    data_class: req.data_class,
    job_id: id,
    request_id: req.request_id,
    status: "QUEUED",
    error_code: null,
    result_json: null,
  });
  getQueue().dispatch(id, "content");
  return queued;
}

export async function processContentJob(jobId: string): Promise<void> {
  const sql = await getSql();
  const jobs = await sql<{
    cancelled: boolean;
    payload_json: string;
    project_id: string;
    status: string;
  }>`select cancelled, payload_json, project_id, status from cos_jobs where job_id = ${jobId}`;
  const job = jobs[0];
  if (!job) return;
  if (job.cancelled) {
    await sql`update cos_jobs set status = ${"CANCELLED"}, updated_at = now() where job_id = ${jobId}`;
    return;
  }
  await sql`update cos_jobs set status = ${"RUNNING"}, updated_at = now() where job_id = ${jobId}`;
  try {
    const req = JSON.parse(job.payload_json) as DraftRequest;
    const bundle = checkBundle(req.evidence);
    const evRow = await sql<{ revoked: boolean }>`
      select revoked from cos_evidence where bundle_id = ${bundle.bundle_id}
    `;
    if (evRow[0]?.revoked) throw new ContractError("SOURCE_REVOKED");
    if (req.budget.max_provider_requests < 1) {
      await sql`
        update cos_jobs set status = ${"BUDGET_EXHAUSTED"}, error_code = ${"BUDGET_EXHAUSTED"}, updated_at = now()
        where job_id = ${jobId}
      `;
      await persistLedger();
      return;
    }
    const eligible = bundle.claims.filter((c) => c.status === "ELIGIBLE" && c.allowed_uses.includes("DRAFT"));
    if (!eligible.length) {
      await sql`
        update cos_jobs set status = ${"BLOCKED_INPUT"}, error_code = ${"MISSING_EVIDENCE"}, updated_at = now()
        where job_id = ${jobId}
      `;
      await persistLedger();
      return;
    }
    const articleId = `art-${req.request_id}`.replace(/[^A-Za-z0-9_.:-]/g, "").slice(0, 80);
    const existing = await sql<{ article_revision: number }>`
      select article_revision from cos_articles where article_id = ${articleId} order by article_revision desc limit 1
    `;
    const rev = (existing[0]?.article_revision ?? 0) + 1;
    const article = generateSyntheticArticle(req.brief, bundle, articleId, rev);
    await insertBrief(req.brief);
    await insertEvidence(bundle);
    await insertArticle(article);
    const json = JSON.stringify(article);
    await putArtifact(req.project_id, `art-${jobId}`, Buffer.from(json), "application/json");
    await sql`
      update cos_jobs
      set status = ${"SUCCEEDED"}, result_json = ${json}, provider_requests = 1, error_code = null, updated_at = now()
      where job_id = ${jobId}
    `;
    await persistLedger();
  } catch (err) {
    const code = err instanceof ContractError ? err.code : "PROVIDER_ERROR";
    safeLog("content.job.fail", { jobId, code });
    await sql`
      update cos_jobs set status = ${"FAILED"}, error_code = ${code}, updated_at = now()
      where job_id = ${jobId}
    `;
    await persistLedger();
  }
}

export async function submitPlanningJob(
  principal: Principal,
  body: unknown,
  idempotencyKey: string,
  contractVersion: string,
): Promise<JobReceipt> {
  await ensureSeed();
  validateHeaderContract(contractVersion);
  const req = validateResearchRequest(body) as unknown as ResearchRequest;
  assertProject(principal, req.project_id);
  const { id, fresh } = await admit(req.project_id, "planning.create", idempotencyKey, req);
  const sql = await getSql();
  if (!fresh) {
    const rows = await sql<Parameters<typeof receipt>[0]>`
      select project_id, data_class, job_id, request_id, status, error_code, result_json from cos_jobs where job_id = ${id}
    `;
    if (rows[0]) return receipt(rows[0]);
  }
  await sql`
    insert into cos_jobs (job_id, project_id, data_class, request_id, kind, status, payload_json, deadline_at)
    values (${id}, ${req.project_id}, ${req.data_class}, ${req.request_id}, ${"planning"}, ${"QUEUED"}, ${JSON.stringify(req)}, ${req.budget.deadline_at})
  `;
  await persistLedger();
  const queued = receipt({
    project_id: req.project_id,
    data_class: req.data_class,
    job_id: id,
    request_id: req.request_id,
    status: "QUEUED",
    error_code: null,
    result_json: null,
  });
  getQueue().dispatch(id, "planning");
  return queued;
}

export async function processPlanningJob(jobId: string): Promise<void> {
  const sql = await getSql();
  const jobs = await sql<{
    cancelled: boolean;
    payload_json: string;
    status: string;
  }>`select cancelled, payload_json, status from cos_jobs where job_id = ${jobId}`;
  const job = jobs[0];
  if (!job) return;
  if (job.cancelled) {
    await sql`update cos_jobs set status = ${"CANCELLED"}, updated_at = now() where job_id = ${jobId}`;
    return;
  }
  if (["SUCCEEDED", "FAILED", "BLOCKED_INPUT", "BUDGET_EXHAUSTED", "TIMED_OUT", "NO_CHANGE"].includes(job.status)) {
    return;
  }
  await sql`update cos_jobs set status = ${"RUNNING"}, updated_at = now() where job_id = ${jobId}`;
  try {
    const req = JSON.parse(job.payload_json) as ResearchRequest;
    const output: PlanningOutput = {
      research: {
        ...kitPlanning.research,
        project_id: req.project_id,
        data_class: req.data_class,
        request_id: req.request_id,
        research_id: `res-${jobId}`.slice(0, 80),
        scope: req.scope,
        keywords: kitPlanning.research.keywords.map((k) => ({
          ...k,
          keyword: req.seeds[0] ?? k.keyword,
          measurement_status: "SYNTHETIC",
          volume: req.data_class === "TEST_ONLY" ? k.volume : null,
          difficulty: req.data_class === "TEST_ONLY" ? k.difficulty : null,
        })),
        warnings: ["SYNTHETIC; not measured SEO data."],
      },
      brief: {
        ...kitBrief,
        project_id: req.project_id,
        data_class: req.data_class,
        brief_id: `brief-${jobId}`.slice(0, 80),
        research_id: `res-${jobId}`.slice(0, 80),
        primary_keyword: req.seeds[0] ?? kitBrief.primary_keyword,
        origin: "RESEARCH",
      },
    };
    if (req.existing_pages.length) {
      output.research.warnings.push("Existing page collision: recommend update, do not force duplicate brief.");
    }
    await insertBrief(output.brief);
    const json = JSON.stringify(output);
    await sql`
      update cos_jobs set status = ${"SUCCEEDED"}, result_json = ${json}, provider_requests = 0, updated_at = now()
      where job_id = ${jobId}
    `;
    await persistLedger();
  } catch (err) {
    const code = err instanceof ContractError ? err.code : "PROVIDER_ERROR";
    await sql`
      update cos_jobs set status = ${"FAILED"}, error_code = ${code}, updated_at = now()
      where job_id = ${jobId}
    `;
    await persistLedger();
  }
}

registerProcessor(async (jobId, kind) => {
  if (kind === "planning") await processPlanningJob(jobId);
  else await processContentJob(jobId);
});


export async function getJob(principal: Principal, jobId: string, contractVersion: string): Promise<JobReceipt> {
  await ensureSeed();
  validateHeaderContract(contractVersion);
  const sql = await getSql();
  const rows = await sql<Parameters<typeof receipt>[0]>`
    select project_id, data_class, job_id, request_id, status, error_code, result_json
    from cos_jobs where job_id = ${jobId}
  `;
  if (!rows[0]) throw new ContractError("VALIDATION_ERROR", "unknown job");
  assertProject(principal, rows[0].project_id);
  return receipt(rows[0]);
}

export async function cancelJob(
  principal: Principal,
  jobId: string,
  idempotencyKey: string,
  contractVersion: string,
): Promise<JobReceipt> {
  await ensureSeed();
  validateHeaderContract(contractVersion);
  const sql = await getSql();
  const rows = await sql<{ project_id: string; status: string }>`
    select project_id, status from cos_jobs where job_id = ${jobId}
  `;
  if (!rows[0]) throw new ContractError("VALIDATION_ERROR", "unknown job");
  assertProject(principal, rows[0].project_id);
  await admit(principal.project_id, "job.cancel", idempotencyKey, { jobId });
  await sql`
    update cos_jobs
    set cancelled = true,
        status = case when status in ('SUCCEEDED','FAILED','CANCELLED','BLOCKED_INPUT','BUDGET_EXHAUSTED','TIMED_OUT','NO_CHANGE') then status else 'CANCELLED' end,
        updated_at = now()
    where job_id = ${jobId}
  `;
  return getJob(principal, jobId, contractVersion);
}

export async function getJobOutput(principal: Principal, jobId: string, contractVersion: string): Promise<unknown> {
  const rec = await getJob(principal, jobId, contractVersion);
  const terminal = ["SUCCEEDED", "FAILED", "CANCELLED", "BLOCKED_INPUT", "BUDGET_EXHAUSTED", "TIMED_OUT", "NO_CHANGE"];
  if (!terminal.includes(rec.status)) throw new ContractError("JOB_NOT_TERMINAL");
  const sql = await getSql();
  const rows = await sql<{ result_json: string | null; project_id: string }>`
    select result_json, project_id from cos_jobs where job_id = ${jobId}
  `;
  assertProject(principal, rows[0].project_id);
  if (!rows[0].result_json) throw new ContractError("VALIDATION_ERROR", "no output");
  return JSON.parse(rows[0].result_json);
}

const briefCache = new Map<string, { at: number; brief: ContentBrief }>();

export async function getBrief(principal: Principal, briefId: string, contractVersion: string): Promise<ContentBrief> {
  await ensureSeed();
  validateHeaderContract(contractVersion);
  const cacheKey = `${principal.project_id}:${briefId}`;
  const hit = briefCache.get(cacheKey);
  if (hit && Date.now() - hit.at < 30_000) {
    assertProject(principal, hit.brief.project_id);
    return hit.brief;
  }
  const sql = await getSql();
  const rows = await sql<{ body_json: string; project_id: string }>`
    select body_json, project_id from cos_briefs
    where brief_id = ${briefId}
    order by brief_revision desc limit 1
  `;
  if (!rows[0]) throw new ContractError("VALIDATION_ERROR", "unknown brief");
  assertProject(principal, rows[0].project_id);
  const brief = JSON.parse(rows[0].body_json) as ContentBrief;
  briefCache.set(cacheKey, { at: Date.now(), brief });
  return brief;
}

export async function listBriefs(principal: Principal): Promise<ContentBrief[]> {
  await ensureSeed();
  const sql = await getSql();
  const rows = await sql<{ body_json: string; brief_id: string; brief_revision: number }>`
    select distinct on (brief_id) body_json, brief_id, brief_revision
    from cos_briefs
    where project_id = ${principal.project_id}
    order by brief_id, brief_revision desc
  `;
  return rows.map((r) => JSON.parse(r.body_json) as ContentBrief);
}

export async function patchBrief(
  principal: Principal,
  briefId: string,
  patch: Partial<Pick<ContentBrief, "title" | "audience" | "primary_keyword" | "proposed_publish_at" | "outline" | "questions">>,
): Promise<ContentBrief> {
  await ensureSeed();
  const current = await getBrief(principal, briefId, CONTRACT_VERSION);
  const next: ContentBrief = {
    ...current,
    ...patch,
    brief_revision: current.brief_revision + 1,
  };
  briefCache.delete(`${principal.project_id}:${briefId}`);
  await insertBrief(next);
  return next;
}

export async function getEvidence(principal: Principal, bundleId: string): Promise<EvidenceBundle> {
  await ensureSeed();
  const sql = await getSql();
  const rows = await sql<{ body_json: string; project_id: string; revoked: boolean }>`
    select body_json, project_id, revoked from cos_evidence where bundle_id = ${bundleId}
  `;
  if (!rows[0]) throw new ContractError("VALIDATION_ERROR", "unknown evidence");
  assertProject(principal, rows[0].project_id);
  const bundle = JSON.parse(rows[0].body_json) as EvidenceBundle;
  if (rows[0].revoked) throw new ContractError("SOURCE_REVOKED");
  return checkBundle(bundle);
}

export async function revokeEvidence(principal: Principal, bundleId: string): Promise<{ bundle_id: string; revoked: true; approvals_revoked: number }> {
  await ensureSeed();
  const sql = await getSql();
  const rows = await sql<{ project_id: string; snapshot_sha256: string; body_json: string }>`
    select project_id, snapshot_sha256, body_json from cos_evidence where bundle_id = ${bundleId}
  `;
  if (!rows[0]) throw new ContractError("VALIDATION_ERROR", "unknown evidence");
  assertProject(principal, rows[0].project_id);
  await sql`update cos_evidence set revoked = true where bundle_id = ${bundleId}`;
  const approvals = await sql<{ approval_id: string; body_json: string }>`
    select approval_id, body_json from cos_approvals
    where project_id = ${rows[0].project_id}
      and evidence_snapshot_sha256 = ${rows[0].snapshot_sha256}
      and decision = ${"APPROVED"}
  `;
  for (const a of approvals) {
    const body = JSON.parse(a.body_json) as ApprovalRecord;
    body.decision = "REVOKED";
    await sql`
      update cos_approvals set decision = ${"REVOKED"}, body_json = ${JSON.stringify(body)}
      where approval_id = ${a.approval_id}
    `;
  }
  await persistLedger();
  return { bundle_id: bundleId, revoked: true, approvals_revoked: approvals.length };
}

export function markSeeded(): void {
  seeded = true;
}

export async function getArticle(principal: Principal, articleId: string, contractVersion: string): Promise<ArticlePackage> {
  await ensureSeed();
  validateHeaderContract(contractVersion);
  const sql = await getSql();
  const rows = await sql<{ body_json: string; project_id: string }>`
    select body_json, project_id from cos_articles
    where article_id = ${articleId}
    order by article_revision desc limit 1
  `;
  if (!rows[0]) throw new ContractError("VALIDATION_ERROR", "unknown article");
  assertProject(principal, rows[0].project_id);
  return JSON.parse(rows[0].body_json) as ArticlePackage;
}

export async function listArticles(principal: Principal): Promise<ArticlePackage[]> {
  await ensureSeed();
  const sql = await getSql();
  const rows = await sql<{ body_json: string }>`
    select distinct on (article_id) body_json
    from cos_articles
    where project_id = ${principal.project_id}
    order by article_id, article_revision desc
  `;
  return rows.map((r) => JSON.parse(r.body_json) as ArticlePackage);
}

export async function editArticle(
  principal: Principal,
  articleId: string,
  expectedRevision: number,
  patch: { title?: string; seoTitle?: string; seoDescription?: string; blockText?: { block_id: string; text: string } },
): Promise<ArticlePackage> {
  await ensureSeed();
  const current = await getArticle(principal, articleId, CONTRACT_VERSION);
  if (current.article_revision !== expectedRevision) {
    throw new ContractError("STALE_REVISION", "optimistic concurrency conflict");
  }
  const blocks = current.blocks.map((b) =>
    patch.blockText && b.block_id === patch.blockText.block_id ? { ...b, text: patch.blockText.text } : b,
  );
  const next = sealArticle({
    ...current,
    article_revision: current.article_revision + 1,
    title: patch.title ?? current.title,
    seo: {
      title: patch.seoTitle ?? current.seo.title,
      description: patch.seoDescription ?? current.seo.description,
    },
    blocks,
    status: "DRAFT",
  });
  const sql = await getSql();
  await sql`update cos_approvals set decision = ${"REVOKED"} where article_id = ${articleId} and decision = ${"APPROVED"}`;
  await insertArticle(next);
  return next;
}

export async function issueApproval(
  principal: Principal,
  articleId: string,
  destinationId: string,
  decision: "APPROVED" | "REJECTED",
): Promise<ApprovalRecord> {
  await ensureSeed();
  requireOk(principal.can_publish, "FORBIDDEN");
  const article = await getArticle(principal, articleId, CONTRACT_VERSION);
  const bundle = await getEvidence(principal, article.bundle_id);
  checkArticle(article, bundle);
  if (decision === "APPROVED") {
    const findings = evaluateArticle(article, bundle);
    if (findings.some((f) => f.blocks_publication) || article.status !== "PREVIEW_READY") {
      throw new ContractError("VALIDATION_ERROR", "article not approvable");
    }
  }
  const record: ApprovalRecord = {
    contract_version: CONTRACT_VERSION,
    project_id: article.project_id,
    data_class: article.data_class,
    approval_id: newId("appr"),
    article_id: article.article_id,
    article_revision: article.article_revision,
    content_sha256: article.content_sha256,
    evidence_snapshot_sha256: article.evidence_snapshot_sha256,
    policy_version: article.policy_version,
    destination_id: destinationId || MOCK_DESTINATION,
    decision,
    approved_by: principal.subject_id,
    approved_at: nowIso(),
    expires_at: new Date(Date.now() + 24 * 3600 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z"),
  };
  const sql = await getSql();
  await sql`
    insert into cos_approvals (
      approval_id, project_id, article_id, article_revision, content_sha256,
      evidence_snapshot_sha256, destination_id, decision, body_json
    ) values (
      ${record.approval_id}, ${record.project_id}, ${record.article_id}, ${record.article_revision},
      ${record.content_sha256}, ${record.evidence_snapshot_sha256}, ${record.destination_id},
      ${record.decision}, ${JSON.stringify(record)}
    )
  `;
  await persistLedger();
  return record;
}

export async function getApproval(approvalId: string): Promise<ApprovalRecord | null> {
  const sql = await getSql();
  const rows = await sql<{ body_json: string }>`select body_json from cos_approvals where approval_id = ${approvalId}`;
  return rows[0] ? (JSON.parse(rows[0].body_json) as ApprovalRecord) : null;
}

export async function submitPublication(
  principal: Principal,
  body: unknown,
  idempotencyKey: string,
  contractVersion: string,
  opts?: { fault?: "none" | "timeout-after-accept" },
): Promise<PublicationReceipt> {
  await ensureSeed();
  validateHeaderContract(contractVersion);
  const req = validatePublishRequest(body) as unknown as PublishRequest;
  assertProject(principal, req.project_id);
  const { id, fresh } = await admit(req.project_id, "publication.submit", idempotencyKey, req);
  const sql = await getSql();
  if (!fresh) {
    const rows = await sql<{ body_json: string }>`select body_json from cos_publications where publication_id = ${id}`;
    if (rows[0]) return JSON.parse(rows[0].body_json) as PublicationReceipt;
  }
  const article = await getArticle(principal, req.article_id, contractVersion);
  const bundle = await getEvidence(principal, article.bundle_id);
  const approval = await getApproval(req.approval_id);
  if (!approval) throw new ContractError("VALIDATION_ERROR", "unknown approval");
  const verdict = gatePublish(article, bundle, req, approval, principal, defaultPolicy(), nowIso());
  const created = nowIso();
  let status: PublicationReceipt["status"] = req.mode === "DRY_RUN" ? "DRY_RUN" : "PUBLISHING";
  let provider_record_id: string | null = null;
  let provider_url: string | null = null;
  let side = 0;
  if (verdict === "DRY_RUN") {
    status = "DRY_RUN";
  } else {
    if (opts?.fault === "timeout-after-accept") setCmsFault("timeout-after-accept");
    try {
      const draft = await cmsCreateDraft({
        projectId: article.project_id,
        destinationId: req.destination_id,
        articleId: article.article_id,
        articleRevision: article.article_revision,
        contentSha256: article.content_sha256,
        body: article.blocks.map((b) => b.text).join("\n"),
      });
      provider_record_id = draft.provider_record_id;
      provider_url = null;
      side = 1;
      status = "PUBLISHED";
    } catch (err) {
      const found = cmsFind({
        projectId: article.project_id,
        destinationId: req.destination_id,
        articleId: article.article_id,
        articleRevision: article.article_revision,
        contentSha256: article.content_sha256,
      });
      if (found) {
        status = "UNKNOWN";
        provider_record_id = found.provider_record_id;
        side = 1;
      } else if (err instanceof ContractError) {
        throw err;
      } else {
        throw new ContractError("PROVIDER_ERROR", "cms", true);
      }
    } finally {
      setCmsFault("none");
    }
  }
  if (status === "PUBLISHED" && (req.mode === "DRY_RUN" || req.data_class === "TEST_ONLY")) {
    // UI must never show LIVE/PUBLISHED for mock TEST_ONLY — keep DRY_RUN label on receipts for TEST_ONLY
    if (req.mode === "DRY_RUN") status = "DRY_RUN";
  }
  const pub: PublicationReceipt = {
    contract_version: CONTRACT_VERSION,
    project_id: req.project_id,
    data_class: req.data_class,
    publication_id: id,
    request_id: req.request_id,
    article_id: req.article_id,
    article_revision: req.article_revision,
    destination_id: req.destination_id,
    content_sha256: req.content_sha256,
    status,
    provider_record_id,
    provider_url,
    created_at: created,
    actual_side_effects: side,
  };
  await sql`
    insert into cos_publications (
      publication_id, project_id, request_id, article_id, article_revision, destination_id,
      content_sha256, status, provider_record_id, provider_url, actual_side_effects, body_json
    ) values (
      ${pub.publication_id}, ${pub.project_id}, ${pub.request_id}, ${pub.article_id}, ${pub.article_revision},
      ${pub.destination_id}, ${pub.content_sha256}, ${pub.status}, ${pub.provider_record_id}, ${pub.provider_url},
      ${pub.actual_side_effects}, ${JSON.stringify(pub)}
    )
    on conflict (publication_id) do nothing
  `;
  await persistLedger();
  return pub;
}

export async function reconcilePublication(principal: Principal, publicationId: string): Promise<PublicationReceipt> {
  await ensureSeed();
  const sql = await getSql();
  const rows = await sql<{ body_json: string; project_id: string }>`
    select body_json, project_id from cos_publications where publication_id = ${publicationId}
  `;
  if (!rows[0]) throw new ContractError("VALIDATION_ERROR", "unknown publication");
  assertProject(principal, rows[0].project_id);
  const pub = JSON.parse(rows[0].body_json) as PublicationReceipt;
  if (pub.status !== "UNKNOWN") return pub;
  if (pub.provider_record_id && cmsRead(pub.provider_record_id)) {
    pub.status = pub.data_class === "TEST_ONLY" ? "DRY_RUN" : "PUBLISHED";
    pub.actual_side_effects = 1;
    await sql`
      update cos_publications set status = ${pub.status}, actual_side_effects = 1, body_json = ${JSON.stringify(pub)}
      where publication_id = ${publicationId}
    `;
  }
  return pub;
}

export async function getPublication(principal: Principal, publicationId: string, contractVersion: string) {
  await ensureSeed();
  validateHeaderContract(contractVersion);
  const sql = await getSql();
  const rows = await sql<{ body_json: string; project_id: string }>`
    select body_json, project_id from cos_publications where publication_id = ${publicationId}
  `;
  if (!rows[0]) throw new ContractError("VALIDATION_ERROR", "unknown publication");
  assertProject(principal, rows[0].project_id);
  return JSON.parse(rows[0].body_json) as PublicationReceipt;
}

export async function listPublications(principal: Principal): Promise<PublicationReceipt[]> {
  await ensureSeed();
  const sql = await getSql();
  const rows = await sql<{ body_json: string }>`
    select body_json from cos_publications where project_id = ${principal.project_id} order by created_at desc
  `;
  return rows.map((r) => JSON.parse(r.body_json) as PublicationReceipt);
}

export async function listJobs(principal: Principal) {
  await ensureSeed();
  const sql = await getSql();
  return sql<{
    job_id: string;
    kind: string;
    status: string;
    request_id: string;
    error_code: string | null;
    provider_requests: number;
    cost_usd: string;
    created_at: string;
  }>`
    select job_id, kind, status, request_id, error_code, provider_requests, cost_usd, created_at::text as created_at
    from cos_jobs where project_id = ${principal.project_id} order by created_at desc limit 50
  `;
}

export async function overview(principal: Principal) {
  await ensureSeed();
  const briefs = await listBriefs(principal);
  const articles = await listArticles(principal);
  const jobs = await listJobs(principal);
  const pubs = await listPublications(principal);
  const blockers = articles.filter((a) => a.status === "REVIEW_REQUIRED").length;
  return {
    mode: "MOCK" as const,
    liveEnabled: false,
    projectId: principal.project_id,
    role: principal.role,
    canPublish: principal.can_publish,
    briefs: briefs.length,
    drafts: articles.length,
    jobs: jobs.length,
    blockers,
    lastSync: nowIso(),
    publications: pubs.length,
    budgetUsd: "0.500000",
  };
}

export async function socialSummary(article: ArticlePackage): Promise<{ text: string; link: string; posting: false }> {
  const firstFact = article.blocks.find((b) => b.kind === "FACTUAL");
  const text = `${article.title}: ${firstFact?.text.slice(0, 120) ?? article.seo.description}`.slice(0, 180);
  requireOk(text.length < article.blocks.map((b) => b.text).join("").length, "VALIDATION_ERROR");
  return { text, link: `https://staging.invalid/${article.slug}`, posting: false };
}

export async function latestApprovalFor(articleId: string, revision: number): Promise<ApprovalRecord | null> {
  const sql = await getSql();
  const rows = await sql<{ body_json: string }>`
    select body_json from cos_approvals
    where article_id = ${articleId} and article_revision = ${revision}
    order by created_at desc limit 1
  `;
  return rows[0] ? (JSON.parse(rows[0].body_json) as ApprovalRecord) : null;
}

export function capabilities() {
  return {
    contract_version: CONTRACT_VERSION,
    service: "content-workflow" as const,
    code_commit: CODE_COMMIT,
    contract_sha256: CONTRACT_SHA256,
    mode: "MOCK" as const,
    enabled_operations: [
      "planning.create",
      "brief.read",
      "content.draft",
      "article.read",
      "approval.issue",
      "publication.dry_run",
      "publication.reconcile",
    ],
    max_json_bytes: 2_097_152,
  };
}

export { hashWithout, redactValue };
