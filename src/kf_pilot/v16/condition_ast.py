from __future__ import annotations

import json
from typing import Any


ALLOWED_COMPARATORS = {"EQ", "NE", "GT", "GTE", "LT", "LTE"}
LEAF_OPS = {"TRUE", "FALSE", "COMPARE", "IN", "UNRESOLVED"}


class ConditionValidationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_ast(node: dict[str, Any], path: str = "$") -> None:
    if not isinstance(node, dict):
        raise ConditionValidationError(f"{path}: node must be an object")
    op = node.get("op")
    if op in {"TRUE", "FALSE"}:
        if set(node) != {"op"}:
            raise ConditionValidationError(f"{path}: {op} cannot contain extra fields")
        return
    if op in {"AND", "OR"}:
        if set(node) != {"op", "args"}:
            raise ConditionValidationError(f"{path}: {op} contains unknown fields")
        args = node.get("args")
        if not isinstance(args, list) or len(args) < 2:
            raise ConditionValidationError(f"{path}: {op} requires at least two args")
        for index, child in enumerate(args):
            validate_ast(child, f"{path}.args[{index}]")
        return
    if op == "NOT":
        if set(node) != {"op", "arg"}:
            raise ConditionValidationError(f"{path}: NOT contains unknown fields")
        if "arg" not in node:
            raise ConditionValidationError(f"{path}: NOT requires arg")
        validate_ast(node["arg"], f"{path}.arg")
        return
    if op == "COMPARE":
        if set(node) - {"op", "field", "comparator", "value", "unit"}:
            raise ConditionValidationError(f"{path}: COMPARE contains unknown fields")
        if not isinstance(node.get("field"), str) or not node["field"]:
            raise ConditionValidationError(f"{path}: COMPARE requires field")
        if node.get("comparator") not in ALLOWED_COMPARATORS:
            raise ConditionValidationError(f"{path}: invalid comparator")
        if "value" not in node:
            raise ConditionValidationError(f"{path}: COMPARE requires value")
        return
    if op == "IN":
        if set(node) != {"op", "field", "values"}:
            raise ConditionValidationError(f"{path}: IN contains unknown fields")
        values = node.get("values")
        if not isinstance(node.get("field"), str) or not node["field"]:
            raise ConditionValidationError(f"{path}: IN requires field")
        if not isinstance(values, list) or not values:
            raise ConditionValidationError(f"{path}: IN requires non-empty values")
        return
    if op == "UNRESOLVED":
        if set(node) - {"op", "legacy_tags", "raw_text", "reason"}:
            raise ConditionValidationError(f"{path}: UNRESOLVED contains unknown fields")
        tags = node.get("legacy_tags")
        if not isinstance(tags, list) or not tags:
            raise ConditionValidationError(f"{path}: UNRESOLVED requires legacy_tags")
        return
    raise ConditionValidationError(f"{path}: unsupported op {op!r}")


def canonicalize_ast(node: dict[str, Any]) -> dict[str, Any]:
    validate_ast(node)
    op = node["op"]
    if op in {"TRUE", "FALSE"}:
        return {"op": op}
    if op == "NOT":
        child = canonicalize_ast(node["arg"])
        if child["op"] == "NOT":
            return canonicalize_ast(child["arg"])
        return {"op": "NOT", "arg": child}
    if op in {"AND", "OR"}:
        flattened: list[dict[str, Any]] = []
        for raw_child in node["args"]:
            child = canonicalize_ast(raw_child)
            if child["op"] == op:
                flattened.extend(child["args"])
            else:
                flattened.append(child)
        unique = {canonical_json(child): child for child in flattened}
        children = [unique[key] for key in sorted(unique)]
        if len(children) == 1:
            return children[0]
        return {"op": op, "args": children}
    if op == "COMPARE":
        result = {
            "op": "COMPARE",
            "field": node["field"].strip().lower(),
            "comparator": node["comparator"],
            "value": node["value"],
        }
        if node.get("unit") is not None:
            result["unit"] = str(node["unit"]).strip().lower()
        return result
    if op == "IN":
        values = sorted({canonical_json(value): value for value in node["values"]}.items())
        return {
            "op": "IN",
            "field": node["field"].strip().lower(),
            "values": [value for _, value in values],
        }
    if op == "UNRESOLVED":
        result = {
            "op": "UNRESOLVED",
            "legacy_tags": sorted({str(tag).strip().upper() for tag in node["legacy_tags"]}),
        }
        if node.get("raw_text"):
            result["raw_text"] = " ".join(str(node["raw_text"]).split())
        result["reason"] = node.get("reason", "CONNECTIVE_UNKNOWN")
        return result
    raise AssertionError("validated AST reached unsupported branch")


def contains_unresolved(node: dict[str, Any]) -> bool:
    node = canonicalize_ast(node)
    if node["op"] == "UNRESOLVED":
        return True
    if node["op"] in {"AND", "OR"}:
        return any(contains_unresolved(child) for child in node["args"])
    if node["op"] == "NOT":
        return contains_unresolved(node["arg"])
    return False


def migrate_legacy_tags(tags: list[str], raw_text: str | None = None) -> dict[str, Any]:
    clean = sorted({str(tag).strip().upper() for tag in tags if str(tag).strip()})
    if not clean and raw_text and raw_text.strip():
        return {
            "op": "UNRESOLVED",
            "legacy_tags": ["RAW_CONDITION_TEXT"],
            "raw_text": raw_text,
            "reason": "RAW_CONDITION_NOT_PARSED",
        }
    if not clean:
        return {"op": "TRUE"}
    if len(clean) == 1:
        return {
            "op": "COMPARE",
            "field": "legacy.tag",
            "comparator": "EQ",
            "value": clean[0],
        }
    return canonicalize_ast(
        {
            "op": "UNRESOLVED",
            "legacy_tags": clean,
            "raw_text": raw_text,
            "reason": "LEGACY_LIST_HAS_NO_BOOLEAN_CONNECTIVE",
        }
    )
