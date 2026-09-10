import { CONTRACT_VERSION, COST_RE, HEX64_RE, ID_RE, SLUG_RE } from "./constants";
import { ContractError, requireOk } from "./errors";
import { instant } from "./clock";

export function noInvalidUnicode(value: unknown): void {
  if (typeof value === "string") {
    for (const ch of value) {
      const c = ch.codePointAt(0) ?? 0;
      requireOk(!(c >= 0xd800 && c <= 0xdfff), "INVALID_UNICODE");
    }
  } else if (Array.isArray(value)) {
    for (const v of value) noInvalidUnicode(v);
  } else if (value && typeof value === "object") {
    for (const [k, v] of Object.entries(value)) {
      noInvalidUnicode(k);
      noInvalidUnicode(v);
    }
  }
}

export function requireKeys(obj: Record<string, unknown>, keys: string[], extraOk = false): void {
  for (const k of keys) {
    if (!(k in obj)) throw new ContractError("VALIDATION_ERROR", `missing ${k}`);
  }
  if (!extraOk) {
    for (const k of Object.keys(obj)) {
      if (!keys.includes(k)) throw new ContractError("VALIDATION_ERROR", `extra field ${k}`);
    }
  }
}

export function requireId(v: unknown, name: string): string {
  requireOk(typeof v === "string" && ID_RE.test(v), "VALIDATION_ERROR", `bad ${name}`);
  return v as string;
}

export function requireHex64(v: unknown, name: string): string {
  requireOk(typeof v === "string" && HEX64_RE.test(v), "VALIDATION_ERROR", `bad ${name}`);
  return v as string;
}

export function requireContractVersion(v: unknown): void {
  if (v !== CONTRACT_VERSION) throw new ContractError("UNSUPPORTED_CONTRACT");
}

export function requireDataClass(v: unknown): "TEST_ONLY" | "STAGING" | "PRODUCTION" {
  requireOk(v === "TEST_ONLY" || v === "STAGING" || v === "PRODUCTION", "VALIDATION_ERROR");
  return v as "TEST_ONLY" | "STAGING" | "PRODUCTION";
}

export function requireAware(v: unknown, name: string): string {
  requireOk(typeof v === "string", "VALIDATION_ERROR", name);
  if (!/[zZ]|[+-]\d{2}:\d{2}$/.test(v as string)) {
    throw new ContractError("VALIDATION_ERROR", "TIMEZONE_REQUIRED");
  }
  instant(v as string);
  return v as string;
}

export function asObject(v: unknown): Record<string, unknown> {
  requireOk(!!v && typeof v === "object" && !Array.isArray(v), "VALIDATION_ERROR");
  return v as Record<string, unknown>;
}

export function validateScope(v: unknown) {
  const o = asObject(v);
  requireKeys(o, ["country_code", "language", "timezone", "domain"]);
  requireOk(o.timezone === "Asia/Bangkok", "VALIDATION_ERROR");
  requireOk(typeof o.country_code === "string" && /^[A-Z]{2}$/.test(o.country_code), "VALIDATION_ERROR");
  requireOk(typeof o.language === "string" && /^[a-z]{2}(-[A-Z]{2})?$/.test(o.language), "VALIDATION_ERROR");
  requireId(o.domain, "domain");
  return o as {
    country_code: string;
    language: string;
    timezone: "Asia/Bangkok";
    domain: string;
  };
}

export function validateBudget(v: unknown) {
  const o = asObject(v);
  requireKeys(o, [
    "max_provider_requests",
    "max_tokens",
    "max_cost_usd",
    "deadline_at",
    "max_transport_attempts",
  ]);
  requireOk(typeof o.max_provider_requests === "number" && o.max_provider_requests >= 0, "VALIDATION_ERROR");
  requireOk(typeof o.max_tokens === "number" && o.max_tokens >= 0, "VALIDATION_ERROR");
  requireOk(typeof o.max_cost_usd === "string" && COST_RE.test(o.max_cost_usd), "VALIDATION_ERROR");
  requireAware(o.deadline_at, "deadline_at");
  requireOk(
    typeof o.max_transport_attempts === "number" &&
      o.max_transport_attempts >= 1 &&
      o.max_transport_attempts <= 3,
    "VALIDATION_ERROR",
  );
  return o;
}

export function validateBrief(v: unknown) {
  noInvalidUnicode(v);
  const o = asObject(v);
  requireContractVersion(o.contract_version);
  requireKeys(o, [
    "contract_version",
    "project_id",
    "data_class",
    "brief_id",
    "brief_revision",
    "research_id",
    "scope",
    "title",
    "audience",
    "intent",
    "primary_keyword",
    "secondary_keywords",
    "questions",
    "outline",
    "evidence_requirements",
    "product_refs",
    "proposed_publish_at",
    "editorial_constraints",
    "origin",
  ]);
  requireId(o.project_id, "project_id");
  requireDataClass(o.data_class);
  requireId(o.brief_id, "brief_id");
  requireOk(typeof o.brief_revision === "number" && o.brief_revision >= 1, "VALIDATION_ERROR");
  requireId(o.research_id, "research_id");
  validateScope(o.scope);
  for (const s of ["title", "audience", "intent", "primary_keyword"] as const) {
    requireOk(typeof o[s] === "string" && (o[s] as string).length >= 1, "VALIDATION_ERROR", s);
  }
  requireOk(o.origin === "RESEARCH" || o.origin === "MANUAL", "VALIDATION_ERROR");
  if (o.proposed_publish_at !== null) requireAware(o.proposed_publish_at, "proposed_publish_at");
  requireOk(Array.isArray(o.questions) && o.questions.length >= 1, "VALIDATION_ERROR");
  requireOk(Array.isArray(o.outline) && o.outline.length >= 1, "VALIDATION_ERROR");
  requireOk(Array.isArray(o.evidence_requirements) && o.evidence_requirements.length >= 1, "VALIDATION_ERROR");
  return o;
}

export function validateBundle(v: unknown) {
  noInvalidUnicode(v);
  const o = asObject(v);
  requireContractVersion(o.contract_version);
  requireKeys(o, [
    "contract_version",
    "project_id",
    "data_class",
    "bundle_id",
    "snapshot_sha256",
    "policy_version",
    "as_of",
    "claims",
    "gaps",
  ]);
  requireId(o.project_id, "project_id");
  requireDataClass(o.data_class);
  requireId(o.bundle_id, "bundle_id");
  requireHex64(o.snapshot_sha256, "snapshot_sha256");
  requireId(o.policy_version, "policy_version");
  requireAware(o.as_of, "as_of");
  requireOk(Array.isArray(o.claims), "VALIDATION_ERROR");
  requireOk(Array.isArray(o.gaps), "VALIDATION_ERROR");
  const claimKeys = [
    "claim_id",
    "text",
    "status",
    "risk",
    "allowed_uses",
    "source_ref",
    "source_version",
    "source_sha256",
    "locator",
    "quote",
    "quote_sha256",
    "applicability",
    "jurisdiction",
  ];
  for (const c of o.claims as unknown[]) {
    const cl = asObject(c);
    requireKeys(cl, claimKeys);
    requireId(cl.claim_id, "claim_id");
    requireOk(["ELIGIBLE", "HOLD", "QUARANTINE"].includes(cl.status as string), "VALIDATION_ERROR");
    requireOk(["DESCRIPTIVE", "PRODUCT_SPEC", "SAFETY", "LEGAL"].includes(cl.risk as string), "VALIDATION_ERROR");
  }
  return o;
}

export function validateArticle(v: unknown) {
  noInvalidUnicode(v);
  const o = asObject(v);
  requireContractVersion(o.contract_version);
  requireKeys(o, [
    "contract_version",
    "project_id",
    "data_class",
    "article_id",
    "article_revision",
    "brief_id",
    "brief_revision",
    "bundle_id",
    "evidence_snapshot_sha256",
    "policy_version",
    "title",
    "slug",
    "status",
    "blocks",
    "seo",
    "unresolved_claim_ids",
    "publication_blockers",
    "content_sha256",
  ]);
  requireId(o.article_id, "article_id");
  requireOk(typeof o.article_revision === "number" && o.article_revision >= 1, "VALIDATION_ERROR");
  requireOk(typeof o.slug === "string" && SLUG_RE.test(o.slug), "VALIDATION_ERROR");
  requireOk(["DRAFT", "PREVIEW_READY", "REVIEW_REQUIRED"].includes(o.status as string), "VALIDATION_ERROR");
  requireHex64(o.content_sha256, "content_sha256");
  const seo = asObject(o.seo);
  requireKeys(seo, ["title", "description"]);
  requireOk(Array.isArray(o.blocks) && o.blocks.length >= 1, "VALIDATION_ERROR");
  for (const b of o.blocks as unknown[]) {
    const bl = asObject(b);
    requireKeys(bl, ["block_id", "kind", "text", "claim_ids"]);
    requireOk(["HEADING", "FACTUAL", "EDITORIAL", "CTA"].includes(bl.kind as string), "VALIDATION_ERROR");
  }
  return o;
}

export function validatePublishRequest(v: unknown) {
  noInvalidUnicode(v);
  const o = asObject(v);
  requireContractVersion(o.contract_version);
  requireKeys(o, [
    "contract_version",
    "project_id",
    "data_class",
    "request_id",
    "article_id",
    "article_revision",
    "content_sha256",
    "evidence_snapshot_sha256",
    "approval_id",
    "destination_id",
    "mode",
    "scheduled_at",
  ]);
  requireOk(["DRY_RUN", "STAGING_DRAFT", "LIVE"].includes(o.mode as string), "VALIDATION_ERROR");
  if (o.scheduled_at !== null) requireAware(o.scheduled_at, "scheduled_at");
  return o;
}

export function validateApproval(v: unknown) {
  noInvalidUnicode(v);
  const o = asObject(v);
  requireContractVersion(o.contract_version);
  requireKeys(o, [
    "contract_version",
    "project_id",
    "data_class",
    "approval_id",
    "article_id",
    "article_revision",
    "content_sha256",
    "evidence_snapshot_sha256",
    "policy_version",
    "destination_id",
    "decision",
    "approved_by",
    "approved_at",
    "expires_at",
  ]);
  requireOk(["APPROVED", "REJECTED", "REVOKED"].includes(o.decision as string), "VALIDATION_ERROR");
  requireAware(o.approved_at, "approved_at");
  requireAware(o.expires_at, "expires_at");
  return o;
}

export function validateDraftRequest(v: unknown) {
  noInvalidUnicode(v);
  const o = asObject(v);
  requireContractVersion(o.contract_version);
  requireKeys(o, [
    "contract_version",
    "project_id",
    "data_class",
    "request_id",
    "brief",
    "evidence",
    "budget",
  ]);
  validateBrief(o.brief);
  validateBundle(o.evidence);
  validateBudget(o.budget);
  return o;
}

export function validateResearchRequest(v: unknown) {
  noInvalidUnicode(v);
  const o = asObject(v);
  requireContractVersion(o.contract_version);
  requireKeys(o, [
    "contract_version",
    "project_id",
    "data_class",
    "request_id",
    "scope",
    "seeds",
    "existing_pages",
    "budget",
  ]);
  validateScope(o.scope);
  validateBudget(o.budget);
  requireOk(Array.isArray(o.seeds), "VALIDATION_ERROR");
  requireOk(Array.isArray(o.existing_pages), "VALIDATION_ERROR");
  return o;
}

export function validateHeaderContract(version: string | null): void {
  if (version !== CONTRACT_VERSION) throw new ContractError("UNSUPPORTED_CONTRACT");
}
