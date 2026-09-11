import { ApiError } from "./errors.ts";
import { hasSurrogates, isId } from "./hash.ts";

const DATA_CLASS = new Set(["TEST_ONLY", "STAGING", "PRODUCTION"]);

function fail(rid: string, msg: string): never {
  throw new ApiError(400, "VALIDATION_ERROR", msg, rid, false);
}

/** Reject naive ISO-8601 instants. Kit JSON Schema format "date-time" does not. */
export function assertAwareInstant(value: string, rid: string, field = "datetime"): string {
  if (typeof value !== "string" || value.length < 10) fail(rid, `${field} must be timezone-aware`);
  if (!/(?:Z|[+-]\d{2}:\d{2})$/.test(value)) {
    fail(rid, `${field} naive datetime rejected`);
  }
  const normalized = value.endsWith("Z") ? `${value.slice(0, -1)}+00:00` : value;
  if (Number.isNaN(Date.parse(normalized))) fail(rid, `${field} invalid`);
  return value;
}

export function assertAwareInstantOrNull(
  value: string | null | undefined,
  rid: string,
  field: string,
): string | null {
  if (value == null || value === "") return null;
  return assertAwareInstant(value, rid, field);
}

export function validateResearchRequest(body: unknown, rid: string): ResearchRequest {
  if (!body || typeof body !== "object") fail(rid, "JSON object required");
  const b = body as Record<string, unknown>;
  if (Object.keys(b).some((k) => !ALLOWED_RR.has(k))) fail(rid, "Unexpected field on ResearchRequest");
  if (hasSurrogates(b)) fail(rid, "INVALID_UNICODE");
  if (b.contract_version !== "1.0.0") {
    throw new ApiError(400, "UNSUPPORTED_CONTRACT", "contract_version must be 1.0.0", rid, false);
  }
  if (typeof b.project_id !== "string" || !isId(b.project_id)) fail(rid, "project_id invalid");
  if (typeof b.data_class !== "string" || !DATA_CLASS.has(b.data_class)) fail(rid, "data_class invalid");
  if (typeof b.request_id !== "string" || !isId(b.request_id)) fail(rid, "request_id invalid");
  const scope = validateScope(b.scope, rid);
  if (!Array.isArray(b.seeds) || b.seeds.length < 1) fail(rid, "seeds required");
  const seeds = b.seeds.map((s) => {
    if (typeof s !== "string" || s.length < 1 || s.length > 12000) fail(rid, "seed invalid");
    return s;
  });
  if (!Array.isArray(b.existing_pages)) fail(rid, "existing_pages required");
  const existing_pages = b.existing_pages.map((p) => validatePage(p, rid));
  const budget = validateBudget(b.budget, rid);
  return {
    contract_version: "1.0.0",
    project_id: b.project_id,
    data_class: b.data_class as ResearchRequest["data_class"],
    request_id: b.request_id,
    scope,
    seeds,
    existing_pages,
    budget,
  };
}

const ALLOWED_RR = new Set([
  "contract_version",
  "project_id",
  "data_class",
  "request_id",
  "scope",
  "seeds",
  "existing_pages",
  "budget",
]);

function validateScope(scope: unknown, rid: string): Scope {
  if (!scope || typeof scope !== "object") fail(rid, "scope required");
  const s = scope as Record<string, unknown>;
  if (Object.keys(s).some((k) => !["country_code", "language", "timezone", "domain"].includes(k))) {
    fail(rid, "Unexpected scope field");
  }
  if (typeof s.country_code !== "string" || !/^[A-Z]{2}$/.test(s.country_code)) fail(rid, "country_code");
  if (typeof s.language !== "string" || !/^[a-z]{2}(-[A-Z]{2})?$/.test(s.language)) fail(rid, "language");
  if (s.timezone !== "Asia/Bangkok") fail(rid, "timezone must be Asia/Bangkok");
  if (typeof s.domain !== "string" || !isId(s.domain)) fail(rid, "domain");
  return s as unknown as Scope;
}

function validatePage(p: unknown, rid: string): ExistingPage {
  if (!p || typeof p !== "object") fail(rid, "page");
  const o = p as Record<string, unknown>;
  if (Object.keys(o).some((k) => !["page_id", "url", "title", "intent"].includes(k))) fail(rid, "page fields");
  if (typeof o.page_id !== "string" || !isId(o.page_id)) fail(rid, "page_id");
  if (typeof o.url !== "string" || !/^https?:\/\//.test(o.url)) fail(rid, "url");
  if (typeof o.title !== "string" || !o.title) fail(rid, "title");
  if (typeof o.intent !== "string" || !o.intent) fail(rid, "intent");
  return o as unknown as ExistingPage;
}

function validateBudget(b: unknown, rid: string): Budget {
  if (!b || typeof b !== "object") fail(rid, "budget required");
  const o = b as Record<string, unknown>;
  const keys = ["max_provider_requests", "max_tokens", "max_cost_usd", "deadline_at", "max_transport_attempts"];
  if (Object.keys(o).some((k) => !keys.includes(k))) fail(rid, "budget fields");
  if (typeof o.max_provider_requests !== "number" || o.max_provider_requests < 0 || o.max_provider_requests > 1000) {
    fail(rid, "max_provider_requests");
  }
  if (typeof o.max_tokens !== "number" || o.max_tokens < 0) fail(rid, "max_tokens");
  if (typeof o.max_cost_usd !== "string" || !/^[0-9]+(\.[0-9]{1,6})?$/.test(o.max_cost_usd)) fail(rid, "max_cost_usd");
  if (typeof o.deadline_at !== "string") fail(rid, "deadline_at must be timezone-aware");
  assertAwareInstant(o.deadline_at, rid, "deadline_at");
  if (typeof o.max_transport_attempts !== "number" || o.max_transport_attempts < 1 || o.max_transport_attempts > 3) {
    fail(rid, "max_transport_attempts");
  }
  return o as unknown as Budget;
}

export type Scope = {
  country_code: string;
  language: string;
  timezone: "Asia/Bangkok";
  domain: string;
};

export type ExistingPage = { page_id: string; url: string; title: string; intent: string };

export type Budget = {
  max_provider_requests: number;
  max_tokens: number;
  max_cost_usd: string;
  deadline_at: string;
  max_transport_attempts: number;
};

export type ResearchRequest = {
  contract_version: "1.0.0";
  project_id: string;
  data_class: "TEST_ONLY" | "STAGING" | "PRODUCTION";
  request_id: string;
  scope: Scope;
  seeds: string[];
  existing_pages: ExistingPage[];
  budget: Budget;
};

export function checkKeywordMetrics(k: {
  measurement_status: string;
  volume: number | null;
  difficulty: number | null;
}): void {
  if (k.measurement_status === "MISSING") {
    if (k.volume !== null || k.difficulty !== null) {
      throw new Error("MISSING_METRIC_NOT_NULL");
    }
  }
}
