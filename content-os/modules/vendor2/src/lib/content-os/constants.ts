export const CONTRACT_VERSION = "1.0.0";
export const CONTRACT_SHA256 =
  "fd3c1b6f1ec5461e7080c538e1c332d7af3098db32edd1565e1ae16933f951a8";
export const SERVICE_NAME = "content-workflow" as const;
export const MAX_JSON_BYTES = 2_097_152;
export const TIMEZONE = "Asia/Bangkok";
export const PILOT_DOMAIN = "manual-chain-hoist";
export const DEFAULT_PROJECT = "test-thbison";
export const POLICY_VERSION = "test-policy-1";
export const MOCK_DESTINATION = "test-cms";
export const STAGING_DESTINATION = "staging-cms";
export const ALLOWED_DESTINATIONS = new Set([MOCK_DESTINATION, STAGING_DESTINATION]);
export const LIVE_FLAGS = {
  allow_live: false,
  allow_staging: false,
  allow_social: false,
};
export const CODE_COMMIT =
  process.env.THBISON_CODE_COMMIT ?? "a7c0e1d2b3f44566778899aabbccddeeff001122";
export const MODE = "MOCK" as const;

export const ENABLED_OPERATIONS = [
  "planning.create",
  "brief.read",
  "content.draft",
  "article.read",
  "approval.issue",
  "publication.dry_run",
  "publication.reconcile",
] as const;

export const ID_RE = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;
export const HEX64_RE = /^[a-f0-9]{64}$/;
export const HEX40_RE = /^[a-f0-9]{40}$/;
export const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
export const COST_RE = /^[0-9]+(\.[0-9]{1,6})?$/;
export const IDEMPOTENCY_RE = /^[\x21-\x7e]{16,128}$/;

export const ERROR_STATUS: Record<string, number> = {
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  VALIDATION_ERROR: 400,
  UNSUPPORTED_CONTRACT: 400,
  IDEMPOTENCY_CONFLICT: 409,
  STALE_REVISION: 409,
  MISSING_EVIDENCE: 422,
  SOURCE_REVOKED: 422,
  BUDGET_EXHAUSTED: 422,
  RATE_LIMITED: 429,
  PROVIDER_ERROR: 503,
  TIMEOUT: 503,
  PUBLICATION_UNKNOWN: 409,
  JOB_NOT_TERMINAL: 409,
};
