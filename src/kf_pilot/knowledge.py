from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable

import pandas as pd

from .core import canonical_json, sha256_text, utc_now


MANUFACTURER_ROLES = {"MANUFACTURER_SPEC", "MANUFACTURER_MANUAL"}

# Deterministic gates only identify source-backed candidate statements. They do
# not rewrite a sentence and never promote a candidate to approved knowledge.
KNOWLEDGE_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("REGULATORY_REQUIREMENT", "rated_capacity_marking", ("capacity must be clearly marked", "rated load marked")),
    ("REGULATORY_REQUIREMENT", "overload_prohibition", ("capacity must not be exceeded", "shall not be loaded beyond", "do not exceed")),
    ("REGULATORY_REQUIREMENT", "inspection_requirement", ("must be regularly inspected", "visual inspection daily", "daily – inspect", "daily - inspect")),
    ("REGULATORY_REQUIREMENT", "support_structure_requirement", ("adequate strength to support", "strong enough to carry the load")),
    ("REGULATORY_REQUIREMENT", "attachment_point_prohibition", ("must not be used as a point of attachment",)),
    ("REGULATORY_REQUIREMENT", "competent_lift_planning", ("properly planned by a competent person",)),
    ("REGULATORY_REQUIREMENT", "thorough_examination", ("thorough examination",)),
    ("REGULATORY_REQUIREMENT", "inspection_recordkeeping", ("records must be kept", "certification record")),
    ("REGULATORY_REQUIREMENT", "static_load_test", ("thử tĩnh 125%", "thử tải tĩnh")),
    ("REGULATORY_REQUIREMENT", "static_load_test", ("tải trọng thử bằng 125%",)),
    ("REGULATORY_REQUIREMENT", "dynamic_load_test", ("tải trọng thử bằng 110%", "thử động 110%")),
    ("REGULATORY_REQUIREMENT", "document_review", ("kiểm tra hồ sơ, lý lịch của thiết bị", "kiểm tra hồ sơ, lý lịch thiết bị")),
    ("REGULATORY_REQUIREMENT", "no_load_test", ("tiến hành thử không tải", "kiểm tra kỹ thuật - thử không tải")),
    ("REGULATORY_REQUIREMENT", "inspection_interval", ("thời hạn kiểm định định kỳ 3 năm", "thời hạn kiểm định định kỳ 1 năm")),
    ("LEGAL_SCOPE", "manual_chain_block_in_scope", ("manually operated chain blocks", "pa lăng xích kéo tay có tải trọng từ 1.000kg trở lên")),
    ("SAFETY_GUIDANCE", "remove_defective_equipment", ("remove it from service", "remove them from service")),
    ("SAFETY_GUIDANCE", "people_lifting_prohibition", ("do not use hoisting equipment for lifting or moving people",)),
    ("SAFETY_GUIDANCE", "personnel_exclusion", ("stand completely clear of the load", "make sure everyone is away from the load", "avoid carrying loads over people")),
    ("SAFETY_GUIDANCE", "vertical_lift_alignment", ("hoist from directly over the load", "straight-line pull must be maintained")),
    ("SAFETY_GUIDANCE", "smooth_operation", ("avoid abrupt, jerky movements", "no sudden acceleration or deceleration")),
)

# Broader concept patterns complement exact phrases. A candidate is admitted
# only when every concept group matches the same source sentence. This expands
# wording coverage without allowing the model to invent or rewrite knowledge.
SEMANTIC_KNOWLEDGE_RULES: tuple[tuple[str, str, tuple[tuple[str, ...], ...]], ...] = (
    ("REGULATORY_REQUIREMENT", "overload_prohibition", (("load", "tai trong"), ("not exceed", "must not exceed", "khong vuot"))),
    ("REGULATORY_REQUIREMENT", "inspection_requirement", (("inspect", "inspection", "kiem tra", "kiem dinh"), ("daily", "regular", "dinh ky", "truoc khi"))),
    ("REGULATORY_REQUIREMENT", "inspection_recordkeeping", (("record", "certificate", "ho so", "ly lich"), ("inspection", "inspect", "kiem tra", "kiem dinh"))),
    ("REGULATORY_REQUIREMENT", "static_load_test", (("static", "tinh"), ("test", "thu"), ("load", "tai"))),
    ("REGULATORY_REQUIREMENT", "dynamic_load_test", (("dynamic", "dong"), ("test", "thu"), ("load", "tai"))),
    ("SAFETY_GUIDANCE", "remove_defective_equipment", (("defect", "damage", "hong", "khuyet tat"), ("remove", "out of service", "ngung su dung", "loai bo"))),
    ("SAFETY_GUIDANCE", "personnel_exclusion", (("person", "people", "nguoi"), ("clear", "away", "khong dung", "tranh xa"), ("load", "tai"))),
    ("SAFETY_GUIDANCE", "people_lifting_prohibition", (("people", "person", "nguoi"), ("lift", "hoist", "nang"), ("do not", "must not", "cam", "khong duoc"))),
)


def _fold(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.replace("đ", "d")
    return re.sub(r"\s+", " ", value).strip()


def _contains_term(text: str, term: str) -> bool:
    folded_term = _fold(term)
    return bool(re.search(rf"(?<!\w){re.escape(folded_term)}(?!\w)", text))


def _matched_rules(quote: str, allowed_families: set[str]) -> set[tuple[str, str]]:
    folded = _fold(quote)
    matches = {
        (family, predicate)
        for family, predicate, needles in KNOWLEDGE_RULES
        if family in allowed_families and any(_fold(needle) in folded for needle in needles)
    }
    matches.update(
        (family, predicate)
        for family, predicate, concept_groups in SEMANTIC_KNOWLEDGE_RULES
        if family in allowed_families
        and all(any(_contains_term(folded, term) for term in group) for group in concept_groups)
    )
    return matches


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\s*[•‣]\s*", text.strip())
    return [re.sub(r"\s+", " ", part).strip() for part in parts if len(part.strip()) >= 25]


def knowledge_candidates(evidence: pd.DataFrame, schema_version: str = "2.0.0") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if evidence.empty:
        return rows
    for evidence_row in evidence.to_dict(orient="records"):
        source_role = str(evidence_row.get("source_role", ""))
        if source_role in MANUFACTURER_ROLES:
            continue
        allowed_families = {
            value.strip() for value in str(evidence_row.get("claim_families", "")).split("|") if value.strip()
        }
        for quote in _sentences(str(evidence_row.get("raw_text", ""))):
            for claim_family, predicate in sorted(_matched_rules(quote, allowed_families)):
                candidate = {
                    "claim_schema_version": schema_version,
                    "target_type": "KNOWLEDGE_ITEM",
                    "claim_family": claim_family,
                    "subject_entity_type": "PRODUCT_FAMILY",
                    "subject_product_family": "manual hand chain hoist",
                    "predicate": predicate,
                    "claim_text": quote,
                    "quote": quote,
                    "evidence_ids": [str(evidence_row["evidence_id"])],
                    "resource_id": str(evidence_row["resource_id"]),
                    "resource_version_hash": str(evidence_row["resource_version_hash"]),
                    "publisher_id": str(evidence_row.get("publisher_id", "")),
                    "publisher_name": str(evidence_row.get("publisher_name", "")),
                    "original_url": str(evidence_row.get("original_url", "")),
                    "source_role": source_role,
                    "authority_tier": str(evidence_row.get("authority_tier", "")),
                    "jurisdiction": str(evidence_row.get("jurisdiction", "")),
                    "applicability_scope": str(evidence_row.get("applicability_scope", "")),
                    "legal_status": str(evidence_row.get("legal_status", "")),
                    "applicability_directness": (
                        "CONDITIONAL" if "CONDITIONAL" in str(evidence_row.get("applicability_scope", "")) else "DIRECT"
                    ),
                    "risk_class": "LEGAL_OR_SAFETY",
                    "decision_state": "REVIEW_REQUIRED",
                    "final_confidence": round(float(evidence_row.get("extraction_confidence", 0)) * 100, 2),
                    "reason_codes": [],
                    "created_at": utc_now(),
                }
                candidate["candidate_id"] = sha256_text(canonical_json(candidate))
                rows.append(candidate)
    return dedupe_knowledge(rows)


def dedupe_knowledge(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for item in candidates:
        key = (
            str(item.get("predicate", "")),
            re.sub(r"\W+", " ", str(item.get("claim_text", "")).casefold()).strip(),
            str(item.get("jurisdiction", "")),
            str(item.get("applicability_scope", "")),
        )
        if key not in seen:
            seen.add(key)
            output.append(item)
    return output


def validate_knowledge(candidates: Iterable[dict[str, Any]], evidence: pd.DataFrame) -> pd.DataFrame:
    evidence_by_id = {str(row["evidence_id"]): row for row in evidence.to_dict(orient="records")}
    validated: list[dict[str, Any]] = []
    for raw in candidates:
        item = dict(raw)
        reasons: list[str] = []
        linked = [evidence_by_id.get(str(value)) for value in item.get("evidence_ids", [])]
        linked = [value for value in linked if value]
        if not linked:
            reasons.append("EVIDENCE_NOT_FOUND")
        elif not any(str(item.get("quote", "")) in str(row.get("raw_text", "")) for row in linked):
            reasons.append("QUOTE_NOT_GROUNDED")
        if item.get("source_role") in MANUFACTURER_ROLES:
            reasons.append("WRONG_SOURCE_ROLE")
        for field in ("authority_tier", "jurisdiction", "applicability_scope", "legal_status"):
            if not str(item.get(field, "")).strip():
                reasons.append(f"MISSING_{field.upper()}")
        identifiers = re.findall(r"\b([A-Z]{1,6})[- ]?\d{2,6}\b", str(item.get("claim_text", "")))
        standard_prefixes = {"TCVN", "QCVN", "QTKD", "CFR", "ISO", "EN", "ASME", "ANSI"}
        if any(prefix.upper() not in standard_prefixes for prefix in identifiers):
            reasons.append("MODEL_SPEC_IN_KNOWLEDGE_PIPELINE")
        item["reason_codes"] = sorted(set(reasons))
        item["decision_state"] = "HOLD" if reasons else "REVIEW_REQUIRED"
        item["validated_at"] = utc_now()
        validated.append(item)
    return pd.DataFrame(validated)
