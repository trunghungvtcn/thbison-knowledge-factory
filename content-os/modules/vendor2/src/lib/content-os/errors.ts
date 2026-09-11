export class ContractError extends Error {
  readonly code: string;
  readonly retryable: boolean;
  constructor(code: string, message?: string, retryable = false) {
    super(message ?? code);
    this.name = "ContractError";
    this.code = code;
    this.retryable = retryable;
  }
}

export function requireOk(ok: boolean, code: string, message?: string): void {
  if (!ok) throw new ContractError(code, message ?? code);
}

const KNOWN = new Set([
  "UNAUTHORIZED",
  "FORBIDDEN",
  "VALIDATION_ERROR",
  "UNSUPPORTED_CONTRACT",
  "IDEMPOTENCY_CONFLICT",
  "STALE_REVISION",
  "MISSING_EVIDENCE",
  "SOURCE_REVOKED",
  "BUDGET_EXHAUSTED",
  "RATE_LIMITED",
  "PROVIDER_ERROR",
  "TIMEOUT",
  "PUBLICATION_UNKNOWN",
  "JOB_NOT_TERMINAL",
]);

export function publicErrorCode(code: string): string {
  if (KNOWN.has(code)) return code;
  if (code.startsWith("SCHEMA_INVALID")) return "VALIDATION_ERROR";
  if (
    [
      "PROJECT_MISMATCH",
      "DATA_CLASS_MISMATCH",
      "STALE_APPROVAL",
      "WRONG_APPROVAL",
      "WRONG_DESTINATION",
      "POLICY_MISMATCH",
      "APPROVAL_NOT_ACTIVE",
      "APPROVAL_EXPIRED",
      "PUBLICATION_BLOCKED",
      "ARTICLE_NOT_READY",
      "NOT_DUE",
      "TEST_DATA_NOT_PUBLISHABLE",
      "LIVE_DISABLED",
      "STAGING_DISABLED",
      "CLAIM_NOT_PUBLISHABLE",
      "RISK_OUT_OF_PILOT_SCOPE",
      "FACT_WITHOUT_CITATION",
      "UNKNOWN_CLAIM",
      "CLAIM_NOT_DRAFTABLE",
      "BLOCKER_NOT_VISIBLE",
      "CONTENT_HASH_MISMATCH",
      "EVIDENCE_HASH_MISMATCH",
      "QUOTE_HASH_MISMATCH",
      "INVALID_UNICODE",
      "TIMEZONE_REQUIRED",
      "NAIVE_DATETIME",
    ].includes(code)
  ) {
    return "VALIDATION_ERROR";
  }
  return "VALIDATION_ERROR";
}

export function isRetryableCode(code: string): boolean {
  return code === "RATE_LIMITED" || code === "PROVIDER_ERROR" || code === "TIMEOUT";
}
