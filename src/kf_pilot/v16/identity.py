from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any
from uuid import UUID, uuid5

from .condition_ast import canonicalize_ast


V16_NAMESPACE = UUID("f24c8211-8795-4dea-b99d-583900000016")


def normalize_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.split()).strip()


def stable_entity_id_from_legacy(legacy_canonical_id: str) -> UUID:
    legacy = normalize_string(legacy_canonical_id)
    if not legacy:
        raise ValueError("legacy canonical ID is required")
    return uuid5(V16_NAMESPACE, f"legacy-canonical:{legacy}")


def semantic_payload(payload: dict[str, Any]) -> dict[str, Any]:
    required = ["product_family", "subject", "predicate", "object_value", "applicability"]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"missing semantic fields: {missing}")
    return {
        "product_family": normalize_string(str(payload["product_family"])) .upper(),
        "subject": normalize_string(str(payload["subject"])) .upper(),
        "predicate": normalize_string(str(payload["predicate"])) .upper(),
        "object_value": payload["object_value"],
        "applicability": normalize_string(str(payload["applicability"])) .upper(),
        "jurisdiction": normalize_string(payload.get("jurisdiction")),
        "legal_status": normalize_string(payload.get("legal_status")),
        "condition_ast": canonicalize_ast(payload.get("condition_ast", {"op": "TRUE"})),
        "exception_ast": canonicalize_ast(payload.get("exception_ast", {"op": "FALSE"})),
    }


def semantic_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        semantic_payload(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return "sh_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def claim_version_id(claim_entity_id: str | UUID, payload: dict[str, Any]) -> str:
    """Return a version ID owned by one entity, even when semantics are shared."""
    entity = str(claim_entity_id)
    digest = semantic_hash(payload)
    return "cv_" + hashlib.sha256(f"{entity}:{digest}".encode("utf-8")).hexdigest()


def legacy_alias_key(legacy_canonical_id: str) -> str:
    value = normalize_string(legacy_canonical_id)
    if not value:
        raise ValueError("legacy canonical ID is required")
    return f"LEGACY_CANONICAL_ID:{value}"


def former_signature_alias_key(signature: str) -> str:
    value = normalize_string(signature)
    if not value:
        raise ValueError("former signature is required")
    return f"FORMER_SIGNATURE:{value}"
