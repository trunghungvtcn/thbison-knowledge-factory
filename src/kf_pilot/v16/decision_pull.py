from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .decisions import DecisionBinding


class DecisionPullError(ValueError):
    pass


@dataclass(frozen=True)
class LiveReviewSnapshot:
    page_id: str
    legacy_id: str
    decision: str
    reviewer_note: str | None
    status: str | None
    reviewed_entity_id: str | None
    reviewed_version_id: str | None


def bind_live_decision(*, snapshot: LiveReviewSnapshot, mapped_page_id: str, claim_entity_id: str) -> DecisionBinding:
    if snapshot.page_id != mapped_page_id:
        raise DecisionPullError("live page does not match publication mapping")
    if snapshot.reviewed_entity_id not in {None, "", claim_entity_id}:
        raise DecisionPullError("review decision belongs to a different entity")
    return DecisionBinding(
        decision=snapshot.decision or "PENDING",
        reviewed_claim_version_id=snapshot.reviewed_version_id or None,
        notes=snapshot.reviewer_note,
    )


def plain_text(prop: dict[str, Any] | None) -> str | None:
    if not prop:
        return None
    kind = prop.get("type")
    if kind in {"title", "rich_text"}:
        return "".join(item.get("plain_text", "") for item in prop.get(kind, [])) or None
    if kind in {"select", "status"}:
        selected = prop.get(kind)
        return selected.get("name") if selected else None
    raise DecisionPullError(f"unsupported live property type: {kind!r}")
