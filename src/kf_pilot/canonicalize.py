from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from typing import Any

import pandas as pd

from .core import canonical_json, sha256_text, utc_now


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "in", "is", "it", "of", "on", "or", "shall", "should", "the", "this", "to", "with",
    "bi", "cac", "cho", "co", "cua", "duoc", "khi", "la", "mot", "nhung", "phai", "tai", "theo", "thi", "trong", "va", "voi",
}

SYNONYMS = {
    "kiem dinh": "inspection", "kiem tra": "inspection", "inspect": "inspection", "inspected": "inspection",
    "thoi han": "interval", "chu ky": "interval", "dinh ky": "periodic",
    "pa lang": "hoist", "chain block": "hoist", "chain fall": "hoist",
    "tai trong": "load", "rated capacity": "rated_load", "rated load": "rated_load",
    "khong duoc": "prohibited", "must not": "prohibited", "do not": "prohibited",
    "thu tinh": "static_test", "static load test": "static_test",
    "thu dong": "dynamic_test", "dynamic load test": "dynamic_test",
    "ho so": "record", "ly lich": "record", "certification record": "record",
}

CONDITION_PATTERNS = {
    "FIXED_INSTALLATION": ("lap dat co dinh", "fixed installation", "fixed hoist"),
    "OUTDOOR": ("ngoai troi", "outdoor"),
    "COVERED": ("mai che", "covered", "indoors", "indoor"),
    "MOBILE_USE": ("su dung luu dong", "mobile use", "portable"),
    "AGE_OVER_12_YEARS": ("tren 12 nam", "over 12 years"),
    "BEFORE_USE": ("truoc khi su dung", "before use"),
    "DAILY": ("hang ngay", "daily"),
    "MONTHLY": ("hang thang", "monthly"),
    "OVERHEAD_GANTRY_SCOPE": ("overhead and gantry",),
}

ACTION_TERMS = (
    "must", "shall", "should", "do not", "inspect", "inspection", "test", "remove", "avoid", "make sure", "includes", "means",
    "hoist", "stand", "plan", "planned", "examine", "examination",
    "phai", "khong duoc", "kiem tra", "kiem dinh", "thu", "tien hanh", "ap dung", "bao gom", "duoc", "la", "co tai trong",
)


def fold_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char)).replace("đ", "d")
    text = re.sub(r"[^a-z0-9.%]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def semantic_text(value: Any) -> str:
    text = f" {fold_text(value)} "
    for source, target in sorted(SYNONYMS.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"(?<!\w){re.escape(source)}(?!\w)", target, text)
    return re.sub(r"\s+", " ", text).strip()


def _number_slots(text: str) -> dict[str, Any]:
    folded = fold_text(text)
    slots: dict[str, Any] = {}
    word_numbers = {"mot": 1.0, "one": 1.0, "ba": 3.0, "three": 3.0}

    def parse_number(raw: str) -> float:
        if re.fullmatch(r"\d+[.,]\d{3}", raw):
            return float(raw.replace(".", "").replace(",", ""))
        return float(raw.replace(",", "."))
    percent = re.search(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*%", folded)
    if percent:
        slots["percent"] = parse_number(percent.group(1))
    duration = re.search(r"(?<!\w)(\d+(?:[.,]\d+)?|mot|one|ba|three)\s*(nam|year|years|thang|month|months|ngay|day|days|phut|minute|minutes)\b", folded)
    date_context = False
    if duration:
        before = folded[max(0, duration.start() - 12):duration.start()]
        after = folded[duration.end():duration.end() + 18]
        date_context = bool(re.search(r"ngay\s+$", before) or re.match(r"\s+\d{1,2}\s+nam\s+\d{4}\b", after))
    if duration and not date_context:
        unit_map = {"nam": "year", "years": "year", "thang": "month", "months": "month", "ngay": "day", "days": "day", "phut": "minute", "minutes": "minute"}
        unit = unit_map.get(duration.group(2), duration.group(2))
        raw_value = duration.group(1)
        slots["duration_value"] = word_numbers.get(raw_value, parse_number(raw_value) if raw_value[0].isdigit() else math.nan)
        slots["duration_unit"] = unit
    capacity = re.search(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(kg|t|ton|tons)\b", folded)
    if capacity:
        value = parse_number(capacity.group(1))
        slots["capacity_kg"] = value * 1000 if capacity.group(2) in {"t", "ton", "tons"} else value
    return slots


def _conditions(text: str) -> list[str]:
    folded = fold_text(text)
    return sorted(name for name, phrases in CONDITION_PATTERNS.items() if any(fold_text(phrase) in folded for phrase in phrases))


def _tokens(text: str) -> set[str]:
    return {token for token in semantic_text(text).split() if token not in STOPWORDS and len(token) > 1}


def _atomicity(text: str, numeric_slots: dict[str, Any]) -> tuple[float, list[str]]:
    folded = fold_text(text)
    reasons = []
    if len(folded.split()) < 4:
        reasons.append("TOO_SHORT")
    if str(text).strip().endswith(":") and not numeric_slots:
        reasons.append("HEADING_OR_FRAGMENT")
    letters = [char for char in str(text) if char.isalpha()]
    if letters and sum(char.isupper() for char in letters) / len(letters) > 0.8:
        reasons.append("HEADING_OR_FRAGMENT")
    if not any(re.search(rf"(?<!\w){re.escape(fold_text(term))}(?!\w)", folded) for term in ACTION_TERMS):
        reasons.append("NO_ACTION_OR_DEFINITION")
    score = max(0.0, 1.0 - 0.34 * len(set(reasons)))
    return round(score, 2), sorted(set(reasons))


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 1.0


def normalize_claims(candidates: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for raw in candidates.to_dict(orient="records"):
        item = dict(raw)
        text = str(item.get("claim_text", ""))
        slots = _number_slots(text)
        conditions = _conditions(text)
        atomicity_score, atomicity_reasons = _atomicity(text, slots)
        item["semantic_text"] = semantic_text(text)
        item["semantic_tokens"] = sorted(_tokens(text))
        item["numeric_slots_json"] = canonical_json(slots)
        item["conditions_json"] = canonical_json(conditions)
        item["atomicity_score"] = atomicity_score
        item["atomicity_reasons"] = atomicity_reasons
        item["canonical_scope_key"] = "|".join([
            str(item.get("subject_product_family", "")), str(item.get("predicate", "")),
            str(item.get("jurisdiction", "")), str(item.get("applicability_scope", "")),
            str(item.get("legal_status", "")),
        ])
        item["variant_id"] = str(item.get("candidate_id") or sha256_text(canonical_json(item)))
        rows.append(item)
    return pd.DataFrame(rows)


def _numeric_relation(left: dict[str, Any], right: dict[str, Any]) -> str:
    shared = set(left) & set(right)
    if not shared:
        return "UNKNOWN"
    return "SAME" if all(left[key] == right[key] for key in shared) else "CONTRADICTS"


def _relation(left: dict[str, Any], right: dict[str, Any]) -> tuple[str, float]:
    if left["canonical_scope_key"] != right["canonical_scope_key"]:
        return "UNRELATED", 0.0
    lt, rt = set(left["semantic_tokens"]), set(right["semantic_tokens"])
    similarity = _jaccard(lt, rt)
    ln, rn = json.loads(left["numeric_slots_json"]), json.loads(right["numeric_slots_json"])
    numeric = _numeric_relation(ln, rn)
    lc, rc = set(json.loads(left["conditions_json"])), set(json.loads(right["conditions_json"]))
    if numeric == "CONTRADICTS" and similarity >= 0.35 and lc == rc:
        return "CONTRADICTS", similarity
    if numeric == "CONTRADICTS" and lc != rc and similarity >= 0.35:
        return ("MORE_SPECIFIC" if lc > rc else "MORE_GENERAL"), similarity
    if numeric == "SAME" and ln and lc == rc:
        return "EQUIVALENT", max(similarity, 0.95)
    if similarity >= 0.82 and lc == rc:
        return "EQUIVALENT", similarity
    if similarity >= 0.58:
        if lc > rc:
            return "MORE_SPECIFIC", similarity
        if rc > lc:
            return "MORE_GENERAL", similarity
        return "SUPPORTING", similarity
    return "UNRELATED", similarity


def canonicalize_knowledge(candidates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    variants = normalize_claims(candidates)
    if variants.empty:
        relation_columns = ["left_variant_id", "right_variant_id", "relation", "similarity", "evaluated_at"]
        return variants, pd.DataFrame(columns=["knowledge_id", "canonical_text", "decision_state"]), pd.DataFrame(columns=relation_columns), pd.DataFrame(columns=relation_columns)
    records = variants.to_dict(orient="records")
    parent = list(range(len(records)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        # Complete-link validation prevents A~B~C from merging when A != C.
        left_members = [i for i in range(len(records)) if find(i) == a]
        right_members = [i for i in range(len(records)) if find(i) == b]
        equivalent = all(
            _relation(records[i], records[j])[0] == "EQUIVALENT"
            for i in left_members for j in right_members
        )
        if a != b and equivalent:
            parent[b] = a

    relations, conflicts = [], []
    groups: dict[str, list[int]] = {}
    for index, row in enumerate(records):
        groups.setdefault(row["canonical_scope_key"], []).append(index)
    for indices in groups.values():
        for offset, left_index in enumerate(indices):
            for right_index in indices[offset + 1:]:
                relation, score = _relation(records[left_index], records[right_index])
                if relation == "UNRELATED":
                    continue
                row = {
                    "left_variant_id": records[left_index]["variant_id"], "right_variant_id": records[right_index]["variant_id"],
                    "relation": relation, "similarity": round(score, 4), "evaluated_at": utc_now(),
                }
                relations.append(row)
                if relation == "EQUIVALENT":
                    union(left_index, right_index)
                elif relation == "CONTRADICTS":
                    conflicts.append(row)

    cluster_members: dict[int, list[int]] = {}
    for index in range(len(records)):
        cluster_members.setdefault(find(index), []).append(index)
    conflict_variants = {item[key] for item in conflicts for key in ("left_variant_id", "right_variant_id")}
    canonicals = []
    cluster_id_by_index: dict[int, str] = {}
    authority_rank = {"PRIMARY_LEGAL": 3, "GOVERNMENT_GUIDANCE": 2, "MANUFACTURER_PRIMARY": 1}
    for member_indices in cluster_members.values():
        members = [records[index] for index in member_indices]
        representative = max(members, key=lambda row: (authority_rank.get(str(row.get("authority_tier")), 0), float(row.get("final_confidence") or 0), -len(str(row.get("claim_text", "")))))
        signature = canonical_json({
            "scope": representative["canonical_scope_key"], "semantic": representative["semantic_text"],
            "numeric": representative["numeric_slots_json"], "conditions": representative["conditions_json"],
        })
        knowledge_id = sha256_text(signature)
        for index in member_indices:
            cluster_id_by_index[index] = knowledge_id
        evidence_ids = sorted({str(value) for row in members for value in (row.get("evidence_ids") or [])})
        resource_ids = sorted({str(row.get("resource_id", "")) for row in members if str(row.get("resource_id", ""))})
        variant_ids = sorted(str(row["variant_id"]) for row in members)
        non_atomic = float(representative.get("atomicity_score") or 0) <= 0.66
        held = any(value in conflict_variants for value in variant_ids) or non_atomic
        reason_codes = []
        if any(value in conflict_variants for value in variant_ids):
            reason_codes.append("CANONICAL_CONFLICT")
        if non_atomic:
            reason_codes.append("NON_ATOMIC_OR_HEADING")
        canonicals.append({
            "knowledge_id": knowledge_id, "candidate_id": knowledge_id,
            "canonical_text": representative.get("claim_text", ""), "claim_text": representative.get("claim_text", ""),
            "claim_family": representative.get("claim_family", ""), "predicate": representative.get("predicate", ""),
            "subject_product_family": representative.get("subject_product_family", ""), "jurisdiction": representative.get("jurisdiction", ""),
            "applicability_scope": representative.get("applicability_scope", ""), "applicability_directness": representative.get("applicability_directness", ""),
            "authority_tier": representative.get("authority_tier", ""), "legal_status": representative.get("legal_status", ""),
            "numeric_slots_json": representative["numeric_slots_json"], "conditions_json": representative["conditions_json"],
            "variant_ids": variant_ids, "variant_count": len(variant_ids), "evidence_ids": evidence_ids,
            "evidence_count": len(evidence_ids), "resource_ids": resource_ids, "resource_count": len(resource_ids),
            "resource_id": resource_ids[0] if resource_ids else "", "original_url": representative.get("original_url", ""),
            "representative_variant_id": representative["variant_id"], "final_confidence": min(float(representative.get("final_confidence") or 0), 99.0),
            "decision_state": "HOLD" if held else "REVIEW_REQUIRED", "risk_class": "LEGAL_OR_SAFETY",
            "atomicity_score": representative.get("atomicity_score", 0),
            "reason_codes": reason_codes, "created_at": utc_now(),
        })
    variants["knowledge_id"] = [cluster_id_by_index[index] for index in range(len(records))]
    relation_columns = ["left_variant_id", "right_variant_id", "relation", "similarity", "evaluated_at"]
    return variants, pd.DataFrame(canonicals), pd.DataFrame(relations, columns=relation_columns), pd.DataFrame(conflicts, columns=relation_columns)
