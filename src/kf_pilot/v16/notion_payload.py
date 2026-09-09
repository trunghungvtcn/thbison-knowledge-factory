from __future__ import annotations

from typing import Any, Iterable

from .notion_adapter import condition_ast_text, typed_system_properties


def _unique_page_mapping(mappings: Iterable[dict[str, Any]]) -> dict[str, str]:
    page_by_entity: dict[str, str] = {}
    entity_by_page: dict[str, str] = {}
    for row in mappings:
        entity_id = row["claim_entity_id"]
        page_id = row["remote_page_id"]
        if entity_id in page_by_entity:
            raise ValueError(f"entity maps to multiple pages: {entity_id}")
        if page_id in entity_by_page and entity_by_page[page_id] != entity_id:
            raise ValueError(f"page maps to multiple entities: {page_id}")
        page_by_entity[entity_id] = page_id
        entity_by_page[page_id] = entity_id
    return page_by_entity


def build_update_only_plan(
    versions: Iterable[dict[str, Any]],
    mappings: Iterable[dict[str, Any]],
    *,
    run_id: str,
    bindings: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Build typed UPDATE operations; never perform HTTP and never create pages."""
    page_by_entity = _unique_page_mapping(mappings)
    binding_by_entity = {row["claim_entity_id"]: row for row in bindings}
    operations: list[dict[str, Any]] = []
    missing_mappings: list[str] = []
    seen_entities = set()

    for version in versions:
        entity_id = version["claim_entity_id"]
        if entity_id in seen_entities:
            raise ValueError("duplicate entity in publication plan")
        seen_entities.add(entity_id)
        page_id = page_by_entity.get(entity_id)
        if not page_id:
            missing_mappings.append(entity_id)
            continue
        semantic = version["semantic_payload"]
        binding = binding_by_entity.get(entity_id, {})
        effective = binding.get("effective_decision", "PENDING")
        if version.get("source_system_status") in {"HOLD", "REJECTED"}:
            system_status = version["source_system_status"]
        elif effective in {"HOLD", "REJECTED", "BLOCKED_BY_SYSTEM_STATUS"}:
            system_status = "REJECTED" if effective == "REJECTED" else "HOLD"
        elif version["condition_unresolved"]:
            system_status = "HOLD_CONDITION_REVIEW"
        elif not version.get("object_value_structured", True):
            system_status = "HOLD_OBJECT_VALUE_REVIEW"
        elif effective == "STALE_REVIEW":
            system_status = "STALE_REVIEW"
        else:
            system_status = "MIGRATED_V16"
        logical = {
            "legacy_id": version["legacy_canonical_id"],
            "claim_entity_id": entity_id,
            "claim_version_id": version["claim_version_id"],
            "canonical_text": version["canonical_text"],
            "condition_ast": condition_ast_text(semantic["condition_ast"]),
            "condition_status": "UNRESOLVED" if version["condition_unresolved"] else "RESOLVED",
            "applicability": semantic["applicability"],
            "system_status": system_status,
            "run_id": run_id,
        }
        operations.append(
            {
                "operation": "UPDATE",
                "page_id": page_id,
                "claim_entity_id": entity_id,
                "claim_version_id": version["claim_version_id"],
                "effective_decision": effective,
                "logical_properties": logical,
                "typed_properties": typed_system_properties(logical),
            }
        )

    return {
        "mode": "NO_WRITE",
        "created_count": 0,
        "updated_count": len(operations),
        "missing_mapping_count": len(missing_mappings),
        "mapping_collision_count": 0,
        "missing_mapping_entity_ids": sorted(missing_mappings),
        "operations": operations,
    }
