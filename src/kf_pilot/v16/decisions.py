from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SYSTEM_OWNED_PROPERTIES = frozenset(
    {
        "Canonical ID",
        "Claim Entity ID",
        "Claim Version ID",
        "Canonical Text",
        "Predicate",
        "Conditions JSON",
        "Applicability",
        "Jurisdiction",
        "Evidence Count",
        "System Status",
        "Last Pipeline Run",
    }
)

HUMAN_OWNED_PROPERTIES = frozenset(
    {
        "Decision",
        "Reviewer",
        "Review Notes",
        "Editorial Notes",
        "Approval Timestamp",
        "Manual Tags",
    }
)


@dataclass(frozen=True)
class DecisionBinding:
    decision: str
    reviewed_claim_version_id: str | None
    notes: str | None = None


def effective_decision(
    *,
    system_status: str,
    current_claim_version_id: str,
    binding: DecisionBinding | None,
    condition_unresolved: bool,
) -> str:
    if system_status in {"HOLD", "REJECTED"}:
        return "BLOCKED_BY_SYSTEM_STATUS"
    if condition_unresolved:
        return "HOLD_CONDITION_REVIEW"
    if binding is None or binding.decision in {"", "PENDING", None}:
        return "PENDING"
    if binding.decision == "APPROVED":
        if binding.reviewed_claim_version_id != current_claim_version_id:
            return "STALE_REVIEW"
        return "APPROVED"
    return binding.decision


def build_notion_update(system_updates: dict[str, Any]) -> dict[str, Any]:
    forbidden = set(system_updates) & HUMAN_OWNED_PROPERTIES
    unknown = set(system_updates) - SYSTEM_OWNED_PROPERTIES
    if forbidden:
        raise ValueError(f"attempt to overwrite human-owned properties: {sorted(forbidden)}")
    if unknown:
        raise ValueError(f"properties not in system allowlist: {sorted(unknown)}")
    return dict(system_updates)
