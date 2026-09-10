"""Explicit public projection. Shared contract 1.0.0 is not modified."""
from __future__ import annotations

# Internal runtime states vs JobReceipt.status enum (contract 1.0.0).
INTERNAL_STATES = (
    "QUEUED",
    "LEASED",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "BLOCKED_INPUT",
)

# JobReceipt.status allowed by frozen schema
CONTRACT_RECEIPT_STATUS = (
    "QUEUED",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "BLOCKED_INPUT",
    "NO_CHANGE",
    "BUDGET_EXHAUSTED",
    "TIMED_OUT",
)

# Projection is an adapter concern, not a contract change.
# OWNER DECISION OPEN: add LEASED to JobReceipt or keep this map.
RECEIPT_PROJECTION = {
    "QUEUED": "QUEUED",
    "LEASED": "QUEUED",  # LEASED absent from JobReceipt enum
    "RUNNING": "RUNNING",
    "SUCCEEDED": "SUCCEEDED",
    "FAILED": "FAILED",
    "CANCELLED": "CANCELLED",
    "BLOCKED_INPUT": "BLOCKED_INPUT",
}

# CapabilitiesReply.service enum only: seo-planning | content-workflow
# OWNER DECISION OPEN: add runtime-orchestrator.
CAPABILITIES_SERVICE_PROJECTION = "content-workflow"
CONTRACT_DECISION_STATUS = "OPEN"


def project_receipt_status(internal: str, error_code: str | None = None) -> str:
    if error_code == "BUDGET_EXHAUSTED" and internal == "FAILED":
        return "BUDGET_EXHAUSTED"
    return RECEIPT_PROJECTION[internal]
