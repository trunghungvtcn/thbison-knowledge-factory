import { createServerFn } from "@tanstack/react-start";
import { getCookie, setCookie } from "@tanstack/react-start/server";
import { principalFromId } from "./authz";
import { CONTRACT_VERSION } from "./constants";
import { ContractError } from "./errors";
import {
  capabilities,
  editArticle,
  ensureSeed,
  getArticle,
  getBrief,
  getEvidence,
  getJob,
  issueApproval,
  latestApprovalFor,
  listArticles,
  listBriefs,
  listJobs,
  listPublications,
  overview,
  patchBrief,
  reconcilePublication,
  socialSummary,
  submitContentJob,
  submitPublication,
} from "./service";
import { getQueue } from "./queue";
import { kitEvidence } from "./fixtures";
import { MOCK_DESTINATION } from "./constants";
import { nowIso } from "./clock";
import { formatBangkok } from "./clock";
import type { ContentBrief } from "./types";

function principal() {
  return principalFromId(getCookie("thbison_principal") ?? "editor");
}

export const getSession = createServerFn({ method: "GET" }).handler(async () => {
  await ensureSeed();
  const p = principal();
  return {
    ...p,
    mode: "MOCK" as const,
    contractVersion: CONTRACT_VERSION,
    now: nowIso(),
    bangkok: formatBangkok(nowIso()),
    capabilities: capabilities(),
  };
});

export const setSession = createServerFn({ method: "POST" })
  .validator((d: { principalId: string }) => d)
  .handler(async ({ data }) => {
    const id = ["editor", "reader", "other"].includes(data.principalId) ? data.principalId : "editor";
    setCookie("thbison_principal", id, { path: "/", httpOnly: true, sameSite: "lax", maxAge: 86400 * 7 });
    return principalFromId(id);
  });

export const loadOverview = createServerFn({ method: "GET" }).handler(async () => {
  return overview(principal());
});

export const loadBriefs = createServerFn({ method: "GET" }).handler(async () => listBriefs(principal()));

export const loadBrief = createServerFn({ method: "GET" })
  .validator((d: { briefId: string }) => d)
  .handler(async ({ data }) => {
    const p = principal();
    const brief = await getBrief(p, data.briefId, CONTRACT_VERSION);
    const bundleId =
      brief.brief_id === "staging-brief-1"
        ? "staging-bundle-1"
        : brief.brief_id === "brief-bao-duong"
          ? "test-bundle-hold"
          : "test-bundle-1";
    const evidence = await getEvidence(p, bundleId).catch(() => kitEvidence);
    return { brief, evidence };
  });

export const saveBrief = createServerFn({ method: "POST" })
  .validator((d: { briefId: string; title?: string; audience?: string; proposed_publish_at?: string | null }) => d)
  .handler(async ({ data }) => {
    return patchBrief(principal(), data.briefId, {
      title: data.title,
      audience: data.audience,
      proposed_publish_at: data.proposed_publish_at ?? undefined,
    });
  });

export const loadArticles = createServerFn({ method: "GET" }).handler(async () => listArticles(principal()));

export const loadArticleWorkspace = createServerFn({ method: "GET" })
  .validator((d: { articleId: string }) => d)
  .handler(async ({ data }) => {
    const p = principal();
    const article = await getArticle(p, data.articleId, CONTRACT_VERSION);
    const evidence = await getEvidence(p, article.bundle_id);
    const approval = await latestApprovalFor(article.article_id, article.article_revision);
    const social = await socialSummary(article);
    return { article, evidence, approval, social, principal: p };
  });

export const generateDraft = createServerFn({ method: "POST" })
  .validator((d: { briefId: string; bundleId?: string }) => d)
  .handler(async ({ data }) => {
    const p = principal();
    const brief = await getBrief(p, data.briefId, CONTRACT_VERSION);
    const bundleId = data.bundleId ?? (brief.brief_id === "staging-brief-1" ? "staging-bundle-1" : brief.brief_id === "brief-bao-duong" ? "test-bundle-hold" : "test-bundle-1");
    const evidence = await getEvidence(p, bundleId).catch(() => kitEvidence);
    const key = `idem-draft-${brief.brief_id}-${brief.brief_revision}-${Date.now()}`.slice(0, 80).padEnd(16, "x");
    const job = await submitContentJob(
      p,
      {
        contract_version: CONTRACT_VERSION,
        project_id: brief.project_id,
        data_class: brief.data_class,
        request_id: `req-${key}`.replace(/[^A-Za-z0-9_.:-]/g, "").slice(0, 80),
        brief,
        evidence,
        budget: {
          max_provider_requests: 3,
          max_tokens: 1000,
          max_cost_usd: "0.500000",
          deadline_at: new Date(Date.now() + 5 * 60 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z"),
          max_transport_attempts: 2,
        },
      },
      key,
      CONTRACT_VERSION,
    );
    await getQueue().drain();
    return getJob(p, job.job_id, CONTRACT_VERSION);
  });

export const saveArticleEdit = createServerFn({ method: "POST" })
  .validator(
    (d: {
      articleId: string;
      expectedRevision: number;
      title?: string;
      seoTitle?: string;
      seoDescription?: string;
      blockId?: string;
      blockText?: string;
    }) => d,
  )
  .handler(async ({ data }) => {
    return editArticle(principal(), data.articleId, data.expectedRevision, {
      title: data.title,
      seoTitle: data.seoTitle,
      seoDescription: data.seoDescription,
      blockText: data.blockId && data.blockText ? { block_id: data.blockId, text: data.blockText } : undefined,
    });
  });

export const decideArticle = createServerFn({ method: "POST" })
  .validator((d: { articleId: string; decision: "APPROVED" | "REJECTED"; destinationId?: string }) => d)
  .handler(async ({ data }) => {
    return issueApproval(principal(), data.articleId, data.destinationId ?? MOCK_DESTINATION, data.decision);
  });

export const publishMock = createServerFn({ method: "POST" })
  .validator((d: { articleId: string; approvalId: string }) => d)
  .handler(async ({ data }) => {
    const p = principal();
    const article = await getArticle(p, data.articleId, CONTRACT_VERSION);
    const approval = await latestApprovalFor(article.article_id, article.article_revision);
    if (!approval || approval.approval_id !== data.approvalId) {
      throw new ContractError("VALIDATION_ERROR", "approval mismatch");
    }
    const key = `idem-pub-${article.article_id}-${article.article_revision}-${approval.approval_id}`.padEnd(16, "x").slice(0, 80);
    return submitPublication(
      p,
      {
        contract_version: CONTRACT_VERSION,
        project_id: article.project_id,
        data_class: article.data_class,
        request_id: `pubreq-${article.article_revision}`.slice(0, 80),
        article_id: article.article_id,
        article_revision: article.article_revision,
        content_sha256: article.content_sha256,
        evidence_snapshot_sha256: article.evidence_snapshot_sha256,
        approval_id: approval.approval_id,
        destination_id: approval.destination_id,
        mode: "DRY_RUN",
        scheduled_at: null,
      },
      key,
      CONTRACT_VERSION,
    );
  });

export const loadHistory = createServerFn({ method: "GET" }).handler(async () => {
  const p = principal();
  const [jobs, pubs] = await Promise.all([listJobs(p), listPublications(p)]);
  return { jobs, pubs };
});

export const loadJob = createServerFn({ method: "GET" })
  .validator((d: { jobId: string }) => d)
  .handler(async ({ data }) => getJob(principal(), data.jobId, CONTRACT_VERSION));

export const runReconcile = createServerFn({ method: "POST" })
  .validator((d: { publicationId: string }) => d)
  .handler(async ({ data }) => reconcilePublication(principal(), data.publicationId));

export type { ContentBrief };
