from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


class NotionAdapterError(ValueError):
    pass


@dataclass(frozen=True)
class PropertyContract:
    logical_name: str
    notion_name: str
    notion_type: str
    owner: str
    required_for_publish: bool = False


CONTRACTS = (
    PropertyContract("legacy_id", "Knowledge ID", "rich_text", "SYSTEM", True),
    PropertyContract("canonical_text", "Claim Text", "rich_text", "SYSTEM", True),
    PropertyContract("applicability", "Applicability Scope", "rich_text", "SYSTEM"),
    PropertyContract("run_id", "Run ID", "rich_text", "SYSTEM"),
    PropertyContract("claim_entity_id", "Claim Entity ID", "rich_text", "SYSTEM", True),
    PropertyContract("claim_version_id", "Claim Version ID", "rich_text", "SYSTEM", True),
    PropertyContract("condition_ast", "Condition AST", "rich_text", "SYSTEM"),
    PropertyContract("condition_status", "Condition Status", "select", "SYSTEM", True),
    PropertyContract("system_status", "System Status", "select", "SYSTEM", True),
    PropertyContract("decision", "Decision", "select", "HUMAN"),
    PropertyContract("reviewer_note", "Reviewer Note", "rich_text", "HUMAN"),
    PropertyContract("reviewed_entity_id", "Reviewed Entity ID", "rich_text", "HUMAN"),
    PropertyContract("reviewed_version_id", "Reviewed Version ID", "rich_text", "HUMAN"),
)
CONTRACT_BY_LOGICAL = {item.logical_name: item for item in CONTRACTS}


def notion_schema_diff(live_schema: dict[str, str]) -> dict[str, Any]:
    additions = []
    type_mismatches = []
    for contract in CONTRACTS:
        current = live_schema.get(contract.notion_name)
        if current is None:
            additions.append({"name": contract.notion_name, "type": contract.notion_type, "owner": contract.owner})
        elif current != contract.notion_type:
            type_mismatches.append({"name": contract.notion_name, "expected": contract.notion_type, "actual": current})
    return {"additions": additions, "type_mismatches": type_mismatches, "compatible": not type_mismatches}


def _rich_text(value: Any) -> dict[str, Any]:
    text = "" if value is None else str(value)
    if len(text) > 2000:
        raise NotionAdapterError("rich_text exceeds Notion 2000-character limit")
    return {"rich_text": [] if not text else [{"type": "text", "text": {"content": text}}]}


def _title(value: Any) -> dict[str, Any]:
    text = str(value)
    if not text or len(text) > 2000:
        raise NotionAdapterError("title must contain 1..2000 characters")
    return {"title": [{"type": "text", "text": {"content": text}}]}


def _select(value: Any) -> dict[str, Any]:
    return {"select": None if value in {None, ""} else {"name": str(value)}}


def typed_system_properties(logical_values: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for logical_name, value in logical_values.items():
        contract = CONTRACT_BY_LOGICAL.get(logical_name)
        if contract is None:
            raise NotionAdapterError(f"unknown logical property: {logical_name}")
        if contract.owner != "SYSTEM":
            raise NotionAdapterError(f"attempt to write human-owned property: {logical_name}")
        encoders = {"rich_text": _rich_text, "title": _title, "select": _select}
        if contract.notion_type not in encoders:
            raise NotionAdapterError(f"unsupported Notion type: {contract.notion_type}")
        result[contract.notion_name] = encoders[contract.notion_type](value)
    return result


def condition_ast_text(ast: dict[str, Any]) -> str:
    return json.dumps(ast, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
