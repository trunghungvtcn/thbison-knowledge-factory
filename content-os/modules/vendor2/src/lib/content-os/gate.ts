import { hashWithout, sha256Utf8 } from "./hash";
import { ContractError, requireOk } from "./errors";
import { instant } from "./clock";
import { LIVE_FLAGS } from "./constants";
import {
  validateArticle,
  validateApproval,
  validateBundle,
  validatePublishRequest,
} from "./validate";
import type { ArticlePackage, ApprovalRecord, EvidenceBundle, Principal, PublishRequest } from "./types";

export function checkBundle(bundle: unknown): EvidenceBundle {
  const raw = validateBundle(bundle);
  const typed = bundle as EvidenceBundle;
  requireOk(typed.snapshot_sha256 === hashWithout(typed as unknown as Record<string, unknown>, "snapshot_sha256"), "EVIDENCE_HASH_MISMATCH");
  const seen = new Set<string>();
  for (const c of typed.claims) {
    requireOk(!seen.has(c.claim_id), "DUPLICATE_CLAIM_ID");
    seen.add(c.claim_id);
    requireOk(sha256Utf8(c.quote) === c.quote_sha256, "QUOTE_HASH_MISMATCH");
    requireOk(c.status === "ELIGIBLE" || c.allowed_uses.length === 0, "INELIGIBLE_CLAIM_HAS_USE");
  }
  void raw;
  return typed;
}

export function checkArticle(article: unknown, bundle: EvidenceBundle): ArticlePackage {
  validateArticle(article);
  checkBundle(bundle);
  const a = article as ArticlePackage;
  requireOk(a.project_id === bundle.project_id, "PROJECT_MISMATCH");
  requireOk(a.data_class === bundle.data_class, "DATA_CLASS_MISMATCH");
  requireOk(a.bundle_id === bundle.bundle_id, "BUNDLE_MISMATCH");
  requireOk(a.evidence_snapshot_sha256 === bundle.snapshot_sha256, "SNAPSHOT_MISMATCH");
  requireOk(a.policy_version === bundle.policy_version, "POLICY_MISMATCH");
  requireOk(a.content_sha256 === hashWithout(a as unknown as Record<string, unknown>, "content_sha256"), "CONTENT_HASH_MISMATCH");
  const claims = Object.fromEntries(bundle.claims.map((c) => [c.claim_id, c]));
  const seen = new Set<string>();
  for (const b of a.blocks) {
    requireOk(!seen.has(b.block_id), "DUPLICATE_BLOCK_ID");
    seen.add(b.block_id);
    if (b.kind === "FACTUAL") requireOk(b.claim_ids.length > 0, "FACT_WITHOUT_CITATION");
    for (const cid of b.claim_ids) {
      requireOk(cid in claims, "UNKNOWN_CLAIM");
      const c = claims[cid];
      requireOk(c.status === "ELIGIBLE" && c.allowed_uses.includes("DRAFT"), "CLAIM_NOT_DRAFTABLE");
    }
  }
  if (a.unresolved_claim_ids.length || a.publication_blockers.length) {
    requireOk(a.status === "REVIEW_REQUIRED", "BLOCKER_NOT_VISIBLE");
  }
  return a;
}

export function sealArticle(article: ArticlePackage): ArticlePackage {
  const next = { ...article };
  next.content_sha256 = hashWithout(next as unknown as Record<string, unknown>, "content_sha256");
  return next;
}

export function sealBundle(bundle: EvidenceBundle): EvidenceBundle {
  const next = { ...bundle };
  next.snapshot_sha256 = hashWithout(next as unknown as Record<string, unknown>, "snapshot_sha256");
  return next;
}

export function gatePublish(
  article: ArticlePackage,
  bundle: EvidenceBundle,
  request: PublishRequest,
  approval: ApprovalRecord,
  principal: Principal,
  policy: { version: string; allow_live: boolean; allow_staging: boolean },
  nowIso: string,
): "DRY_RUN" | "AUTHORIZED" {
  validatePublishRequest(request);
  validateApproval(approval);
  checkArticle(article, bundle);
  requireOk(principal.project_id === article.project_id, "FORBIDDEN");
  requireOk(principal.can_publish === true, "FORBIDDEN");
  requireOk(
    request.project_id === article.project_id && article.project_id === approval.project_id,
    "PROJECT_MISMATCH",
  );
  requireOk(
    request.data_class === article.data_class && article.data_class === approval.data_class,
    "DATA_CLASS_MISMATCH",
  );
  for (const field of ["article_id", "article_revision", "content_sha256", "evidence_snapshot_sha256"] as const) {
    requireOk(request[field] === article[field] && article[field] === approval[field], "STALE_APPROVAL");
  }
  requireOk(request.approval_id === approval.approval_id, "WRONG_APPROVAL");
  requireOk(request.destination_id === approval.destination_id, "WRONG_DESTINATION");
  requireOk(
    approval.policy_version === article.policy_version && article.policy_version === policy.version,
    "POLICY_MISMATCH",
  );
  requireOk(approval.decision === "APPROVED", "APPROVAL_NOT_ACTIVE");
  const t = instant(nowIso);
  requireOk(instant(approval.approved_at) <= t && t < instant(approval.expires_at), "APPROVAL_EXPIRED");
  requireOk(!article.publication_blockers.length && !article.unresolved_claim_ids.length, "PUBLICATION_BLOCKED");
  requireOk(article.status === "PREVIEW_READY", "ARTICLE_NOT_READY");
  if (request.scheduled_at !== null) {
    requireOk(instant(request.scheduled_at) <= t, "NOT_DUE");
  }
  const used = new Set(article.blocks.flatMap((b) => b.claim_ids));
  for (const c of bundle.claims) {
    if (used.has(c.claim_id)) {
      requireOk(c.allowed_uses.includes("PUBLISH"), "CLAIM_NOT_PUBLISHABLE");
      requireOk(c.risk !== "SAFETY" && c.risk !== "LEGAL", "RISK_OUT_OF_PILOT_SCOPE");
    }
  }
  if (request.mode === "DRY_RUN") return "DRY_RUN";
  if (request.mode === "LIVE") {
    requireOk(article.data_class === "PRODUCTION", "TEST_DATA_NOT_PUBLISHABLE");
    requireOk(policy.allow_live === true, "LIVE_DISABLED");
  }
  if (request.mode === "STAGING_DRAFT") {
    requireOk(article.data_class === "STAGING", "TEST_DATA_NOT_PUBLISHABLE");
    requireOk(policy.allow_staging === true, "STAGING_DISABLED");
  }
  return "AUTHORIZED";
}

export function defaultPolicy() {
  return { version: "test-policy-1", ...LIVE_FLAGS };
}

export function mapGateError(err: unknown): ContractError {
  if (err instanceof ContractError) return err;
  const code = err instanceof Error && "code" in err ? String((err as { code: string }).code) : "VALIDATION_ERROR";
  return new ContractError(code, err instanceof Error ? err.message : String(err));
}
