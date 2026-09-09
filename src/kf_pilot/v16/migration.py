from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from pydantic import BaseModel, Field

from .condition_ast import canonicalize_ast, contains_unresolved, migrate_legacy_tags
from .decisions import DecisionBinding, effective_decision
from .identity import (
    claim_version_id,
    former_signature_alias_key,
    legacy_alias_key,
    semantic_hash,
    stable_entity_id_from_legacy,
)
from .object_value import normalize_object_value


class LegacyCanonicalRow(BaseModel):
    legacy_canonical_id: str
    canonical_text: str
    product_family: str = "MANUAL_CHAIN_HOIST"
    subject: str = "MANUAL_CHAIN_HOIST"
    predicate: str
    object_value: Any
    jurisdiction: str | None = None
    applicability: str = "GENERIC"
    legal_status: str | None = None
    condition_tags: list[str] = Field(default_factory=list)
    condition_raw_text: str | None = None
    parsed_condition_ast: dict[str, Any] | None = None
    exception_ast: dict[str, Any] = Field(default_factory=lambda: {"op": "FALSE"})
    former_signatures: list[str] = Field(default_factory=list)
    system_status: str = "REVIEW_REQUIRED"
    decision: str = "PENDING"
    reviewed_claim_version_id: str | None = None
    notes: str | None = None
    notion_page_id: str | None = None


@dataclass(frozen=True)
class MigrationResult:
    entity: dict[str, Any]
    version: dict[str, Any]
    aliases: list[dict[str, Any]]
    decision_binding: dict[str, Any]
    publication_mapping: dict[str, Any] | None
    issues: list[dict[str, Any]]


def migrate_row(row: LegacyCanonicalRow, run_id: str) -> MigrationResult:
    entity_id = stable_entity_id_from_legacy(row.legacy_canonical_id)
    condition_ast = canonicalize_ast(
        row.parsed_condition_ast
        if row.parsed_condition_ast is not None
        else migrate_legacy_tags(row.condition_tags, row.condition_raw_text)
    )
    exception_ast = canonicalize_ast(row.exception_ast)
    object_value, object_issues = normalize_object_value(row.object_value)
    semantic = {
        "product_family": row.product_family,
        "subject": row.subject,
        "predicate": row.predicate,
        "object_value": object_value,
        "applicability": row.applicability,
        "jurisdiction": row.jurisdiction,
        "legal_status": row.legal_status,
        "condition_ast": condition_ast,
        "exception_ast": exception_ast,
    }
    semantic_digest = semantic_hash(semantic)
    version_id = claim_version_id(entity_id, semantic)
    unresolved = contains_unresolved(condition_ast) or contains_unresolved(exception_ast)
    binding = DecisionBinding(
        decision=row.decision,
        # Do not manufacture proof that a legacy approval reviewed this V16
        # semantic version. A missing binding intentionally becomes stale.
        reviewed_claim_version_id=row.reviewed_claim_version_id,
        notes=row.notes,
    )
    effective = effective_decision(
        system_status=row.system_status,
        current_claim_version_id=version_id,
        binding=binding,
        condition_unresolved=unresolved,
    )
    issues: list[dict[str, Any]] = []
    if unresolved:
        issues.append(
            {
                "code": "CONDITION_CONNECTIVE_UNRESOLVED",
                "legacy_canonical_id": row.legacy_canonical_id,
                "claim_entity_id": str(entity_id),
                "blocking": True,
            }
        )
    for code in object_issues:
        issues.append(
            {
                "code": code,
                "legacy_canonical_id": row.legacy_canonical_id,
                "claim_entity_id": str(entity_id),
                "blocking": True,
            }
        )

    mapping = None
    aliases = [
        {
            "alias_key": legacy_alias_key(row.legacy_canonical_id),
            "alias_type": "LEGACY_CANONICAL_ID",
            "alias_value": row.legacy_canonical_id,
            "claim_entity_id": str(entity_id),
            "first_seen_run_id": run_id,
        }
    ]
    for signature in sorted(set(row.former_signatures)):
        aliases.append(
            {
                "alias_key": former_signature_alias_key(signature),
                "alias_type": "FORMER_SIGNATURE",
                "alias_value": signature,
                "claim_entity_id": str(entity_id),
                "first_seen_run_id": run_id,
            }
        )
    if row.notion_page_id:
        mapping = {
            "target": "NOTION_KNOWLEDGE_ITEMS",
            "claim_entity_id": str(entity_id),
            "remote_page_id": row.notion_page_id,
        }
        aliases.append(
            {
                "alias_key": f"NOTION_PAGE_ID:{row.notion_page_id}",
                "alias_type": "NOTION_PAGE_ID",
                "alias_value": row.notion_page_id,
                "claim_entity_id": str(entity_id),
                "first_seen_run_id": run_id,
            }
        )

    return MigrationResult(
        entity={
            "claim_entity_id": str(entity_id),
            "product_family": row.product_family,
            "created_from_legacy_id": row.legacy_canonical_id,
            "current_claim_version_id": version_id,
        },
        version={
            "claim_version_id": version_id,
            "semantic_hash": semantic_digest,
            "claim_entity_id": str(entity_id),
            "legacy_canonical_id": row.legacy_canonical_id,
            "canonical_text": row.canonical_text,
            "semantic_payload": semantic,
            "condition_unresolved": unresolved,
            "object_value_structured": not object_issues,
            "source_system_status": row.system_status,
            "migration_run_id": run_id,
        },
        aliases=aliases,
        decision_binding={
            "claim_entity_id": str(entity_id),
            "reviewed_claim_version_id": row.reviewed_claim_version_id,
            "decision": row.decision,
            "effective_decision": effective,
            "notes": row.notes,
        },
        publication_mapping=mapping,
        issues=issues,
    )


def result_as_dict(result: MigrationResult) -> dict[str, Any]:
    return asdict(result)
