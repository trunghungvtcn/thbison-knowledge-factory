export const ERROR_CODES = [
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
] as const;

export type ErrorCode = (typeof ERROR_CODES)[number];

export class ApiError extends Error {
  readonly http: number;
  readonly code: ErrorCode;
  readonly retryable: boolean;
  readonly request_id: string;

  constructor(http: number, code: ErrorCode, message: string, request_id: string, retryable = false) {
    super(message);
    this.http = http;
    this.code = code;
    this.retryable = retryable;
    this.request_id = request_id;
  }

  body() {
    return {
      contract_version: "1.0.0",
      request_id: this.request_id,
      code: this.code,
      message: this.message.slice(0, 12000),
      retryable: this.retryable,
    };
  }
}

export function jsonResponse(status: number, body: unknown, extra?: HeadersInit): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      ...extra,
    },
  });
}
