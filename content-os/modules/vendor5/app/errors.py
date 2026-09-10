from __future__ import annotations


class AdapterError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False, http_status: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.http_status = http_status or STATUS.get(code, 400)

    def body(self, request_id: str = "unknown") -> dict:
        return {
            "contract_version": "1.0.0",
            "request_id": request_id,
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }


STATUS = {
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "VALIDATION_ERROR": 400,
    "UNSUPPORTED_CONTRACT": 400,
    "IDEMPOTENCY_CONFLICT": 409,
    "STALE_REVISION": 409,
    "MISSING_EVIDENCE": 422,
    "SOURCE_REVOKED": 422,
    "BUDGET_EXHAUSTED": 422,
    "RATE_LIMITED": 429,
    "PROVIDER_ERROR": 503,
    "TIMEOUT": 503,
    "PUBLICATION_UNKNOWN": 409,
    "JOB_NOT_TERMINAL": 409,
    "SCHEMA_DRIFT": 422,
    "APPROVAL_EXPIRED": 422,
    "APPROVAL_REVOKED": 422,
    "APPROVAL_NOT_ACTIVE": 422,
    "STALE_APPROVAL": 422,
    "POLICY_MISMATCH": 422,
    "DATA_CLASS_MISMATCH": 422,
    "PROJECT_MISMATCH": 403,
    "DESTINATION_DENIED": 403,
    "LIVE_DISABLED": 403,
    "STAGING_DISABLED": 403,
    "UNSAFE_CONTENT": 422,
    "ASSET_HASH_MISMATCH": 422,
    "SCHEDULE_INVALID": 400,
    "CAPABILITY_MISMATCH": 422,
    "UNKNOWN_OUTCOME": 409,
    "BLOCKED_MISSING_INPUT": 422,
    "BLOCKED_ACCESS": 403,
}
