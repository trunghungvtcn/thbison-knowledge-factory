"""Fail-closed Knowledge output to Content OS EvidenceBundle 1.0.0 mapping."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


class EvidenceMappingError(ValueError):
    """Raised when the envelope cannot be mapped without inventing identity."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha256(value: Any) -> str:
    raw = value if isinstance(value, bytes) else _canonical(value)
    return hashlib.sha256(raw).hexdigest()


def map_knowledge_output(output: dict[str, Any], *, expected_project_id: str) -> dict[str, Any]:
    """Map a pinned Knowledge output without upgrading holds or missing evidence.

    The accepted source envelope is intentionally small and explicit. Real Notion
    payloads must first be normalized by the Knowledge repository; this gateway
    never guesses database/page identity from a Content OS brief.
    """

    if output.get("data_class") != "TEST_ONLY":
        raise EvidenceMappingError("ONLY_TEST_ONLY_ACCEPTED")
    if output.get("project_id") != expected_project_id:
        raise EvidenceMappingError("PROJECT_MISMATCH")
    revision = str(output.get("knowledge_revision") or "").strip()
    policy = str(output.get("policy_version") or "").strip()
    as_of = str(output.get("as_of") or "").strip()
    if not revision or not policy or not as_of:
        raise EvidenceMappingError("MISSING_REVISION_POLICY_OR_AS_OF")

    mapped: list[dict[str, Any]] = []
    gaps: list[str] = list(output.get("gaps") or [])
    for index, raw in enumerate(output.get("claims") or []):
        claim_id = str(raw.get("claim_id") or f"missing-{index}")
        text = str(raw.get("text") or raw.get("quote") or "").strip()
        source = raw.get("source") or {}
        source_ref = str(source.get("id") or "").strip()
        source_version = str(source.get("revision") or "").strip()
        source_sha = str(source.get("sha256") or "").lower()
        locator = str(source.get("locator") or "").strip()
        quote = str(raw.get("quote") or text).strip()
        quote_sha = str(raw.get("quote_sha256") or "").lower()
        computed_quote_sha = hashlib.sha256(quote.encode("utf-8")).hexdigest()
        provenance_ok = (
            bool(text and source_ref and source_version and locator and quote)
            and len(source_sha) == 64
            and all(c in "0123456789abcdef" for c in source_sha)
            and quote_sha == computed_quote_sha
            and raw.get("provenance_verified") is True
        )
        upstream_status = str(raw.get("status") or "HOLD").upper()
        eligible = provenance_ok and upstream_status == "ELIGIBLE"
        if not provenance_ok:
            gaps.append(f"{claim_id}:MISSING_OR_UNVERIFIED_PROVENANCE")
        if upstream_status in {"HUMAN_HOLD", "REVIEW_REQUIRED", "HOLD", "QUARANTINE"}:
            eligible = False
        mapped.append(
            {
                "claim_id": claim_id,
                "text": text or "Missing evidence text",
                "status": "ELIGIBLE" if eligible else "HOLD",
                "risk": raw.get("risk") if raw.get("risk") in {"DESCRIPTIVE", "PRODUCT_SPEC", "SAFETY", "LEGAL"} else "DESCRIPTIVE",
                "allowed_uses": ["DRAFT"] if eligible else [],
                "source_ref": source_ref or "missing-source",
                "source_version": source_version or "missing-revision",
                "source_sha256": source_sha if len(source_sha) == 64 else "0" * 64,
                "locator": locator or "missing://blocked",
                "quote": quote or "Missing evidence quote",
                "quote_sha256": computed_quote_sha,
                "applicability": str(raw.get("applicability") or "TEST_ONLY fixture"),
                "jurisdiction": str(raw.get("jurisdiction") or "TEST_ONLY"),
            }
        )

    body: dict[str, Any] = {
        "contract_version": "1.0.0",
        "project_id": expected_project_id,
        "data_class": "TEST_ONLY",
        "bundle_id": f"kb-{_sha256([expected_project_id, revision, mapped])[:20]}",
        "snapshot_sha256": "0" * 64,
        "policy_version": policy,
        "as_of": as_of,
        "claims": mapped,
        "gaps": sorted(set(str(g) for g in gaps if str(g))),
    }
    sealed = deepcopy(body)
    sealed.pop("snapshot_sha256", None)
    body["snapshot_sha256"] = _sha256(sealed)
    return body
